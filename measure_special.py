# -*- coding: utf-8 -*-
import sys,time,os
import threading
import numpy as np
import random

from instrument import instrument
from base_function import base_function

class measure(instrument,base_function):
    '''测量，1.电阻随磁场变化，2.加脉冲电流，磁场，测量电阻'''
    #测量电阻随磁场变化
    def __init__(self):
        super(measure,self).__init__()
        self.n_func=0 #功能选择，0.电流回线，1.正负脉冲
        self.n_average=100 #多次测量，取平均值次数
        #励磁电源部分
        self.i_Magnet_min=-4.4 #0.08 #磁铁加的最小电流
        self.i_Magnet_max=4.4 #0.06 #磁铁加的最大电流
        self.n_Magnet=40 #磁铁从最小电流到最大电流之间点的数目  #细扫40个点
        self.i_Magnet_list_fine=[[-5.5,-5.3,3],[5.3,5.5,3]] #细扫
        self.B_Magnet_list=[[-300,300,30],[300,-300,30]]
        #self.ratio=9.1  #励磁电源电压与电流的比值，不能超过12,已弃用，电压改为加到最大值

        #纵向电流部分
        self.i_output=0.2e-3  #
        self.i_heat=10e-3  #纵向输出电流，单位A
        self.width=50.0/1000 #纵向电流脉冲宽度

        #AHE测量相关
        self.loop_time_AHE=1
        #脉冲相关
        self.i_pulse_max=6e-3 #脉冲的最高值（-0.105到0.105A)
        self.i_pulse_min=-6e-3 #脉冲的最低值，还未启用
        self.i_pulse_list=[[-10,10,21]]#用于生成脉冲电流列表
        self.i_pulse_width=1e-3 #脉冲宽度（0,0.001到999s）
        self.i_pulse_gap_time=2 #两次脉冲之间的间隔时间
        self.n_pulse=21 #脉冲总数目
        self.i_Magnet_assist=1#辅助磁场需要加的电流    
        self.B_Magnet_assist=100 #辅助场大小
        self.B_Magnet_assist_list=[0,100]
        self.loop_time=1#扫脉冲循环次数
        #脉冲循环测量
        #随时间测量部分
        self.time_list=[[0.01,0.1,11]]#单位s
        self.i_mea=0.2e-3#测量电流 A
        self.i_pulse=1e-3#脉冲电流 A
        self.V_range='0.1'
        #正负脉冲测量
        self.n_pulse_half_cycle=2 #半个周期内脉冲数
        self.n_mea_after_pulse=2 #一个脉冲后测量几个点
        #扫辅助场和辅助电流
        self.i_B_list=[0.038,0.4,0.9,1.3]
        self.i_output_list=[10e-3,20e-3,30e-3,50e-3,70e-3]   
        #谐波
        self.harm=1#谐波次数
        self.i_harm_list=[0.0005,0.001,0.0015] #正弦电流有效值
        self.freq=133
        #SMR相关
        self.i_Magnet=1
        self.toward=0#旋转方向 0:角度增加 1:角度减少
        self.speed=150#旋转速度
        self.angle_one=5 #单次旋转的角度
        self.subdivision=2 #细分数
        self.sum_angle=0 #角度累计
        self.wait_time_angle=1.5 #每次转动后的等待时间
        self.angle_list=[[0,360,73]]
        #辅助参数
        self.wait_time=0.3  #一些要等待的地方的等待时间
        self.t_heat=120
        self.if_DC=0
        self.thread=False #用于存放多线程
        self.error=1.3  
        self.Hz=20
    def init_set_i_Magnet_list(self):
        #生成励磁电流列表
        if(self.n_Magnet>0 or not self.i_Magnet_list_fine):
            self.i_Magnet_list=np.linspace(self.i_Magnet_min,self.i_Magnet_max,self.n_Magnet)          
            self.i_Magnet_list=np.append(self.i_Magnet_list,self.i_Magnet_list[::-1]) 
            print('励磁电流列表为',self.i_Magnet_list)          
        elif(self.n_Magnet==0):
            self.i_Magnet_list=self.creat_list(self.i_Magnet_list_fine,name='励磁电流',if_loop=1)
        elif(self.n_Magnet==-2):
            self.i_Magnet_list=self.creat_list(self.i_Magnet_list_fine,name='励磁电流',if_loop=0)
        else:
            #设置磁场模式
            i_Magnet_list=[]      
            B_temp=None#用于存放边界处的磁场值  
            I_temp=None#用于存放边界处的励磁电流
            if(self.n_Magnet==-1):
                B_Magnet_list=self.B_Magnet_list
            else:
                temp=[]
                for B_i in self.B_Magnet_list:
                    temp.append([B_i[1],B_i[0],B_i[2]])
                B_Magnet_list=self.B_Magnet_list+temp[::-1]
                print(B_Magnet_list)
            for B_range in B_Magnet_list:
                if(B_range[0]==B_temp):
                    #如果两个区间交界处磁场一样，不重复定值
                    I_start=I_temp
                else:
                    I_start=self.set_B_Magnet(B_range[0],if_exact=0,error=2)[1]   
                I_stop=self.set_B_Magnet(B_range[1],if_exact=0,error=2)[1]  
                B_temp=B_range[1]    
                I_temp=I_stop                       
                i_Magnet_list.append([I_start,I_stop,B_range[2]])
            print(i_Magnet_list)
            self.i_Magnet_list=self.creat_list(i_Magnet_list,name='励磁电流',if_loop=0)   

    '''一、改变磁场，测量电阻，如反常霍尔'''
    def R_H(self,i_Magnet_list):
        #给定磁场列表，测定不同磁场下的电阻
        if self.if_DC:
            self.set_i_DC(i_output=self.i_mea)
        for i_Magnet in i_Magnet_list:
            self.set_i_Magnet(i_Magnet)
            H=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场和电阻
            if self.if_DC:
                R=self.mea_V()/self.i_mea#self.mea_R(i_output=self.i_mea)
            else:
                R=self.mea_R(i_output=self.i_mea)
            self.i_count+=1
            self.data.append([H,R])
            print('第{}次测量'.format(self.i_count))
            print('励磁电流:{:g},磁场:{:.4f},电阻:{:.8e}'.format(i_Magnet,H,R))  
        self.save_data(self.data)
    def AHE(self):
        #测量电阻随磁场的变化，如AHE、PHE
        self.init_common()
        self.link_ins(ins=['2182A','F1208高斯计','KEPCO电流源'])#连接仪器
        self.link_ins_or(ins=['6221','2611A'])#根据实际连接选择电流源
        self.init_set_i_Magnet_list()

        #预处理，第一个点有跳动，测两次
        self.set_i_Magnet(self.i_Magnet_list[0])
        B=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场和电阻
        R=self.mea_V()/self.i_mea
        
        for i in range(self.loop_time):
            self.R_H(self.i_Magnet_list)
        self.loop=0
    def creat_H_list(self,H_list,Hz=20):
        B1_temp=0
        for i in range(len(H_list)):
            B0=H_list[i][0]
            B1=H_list[i][1]
            if(B0==0):
                B0=0.1*np.sign(B1)
            if(B1==0):
                B1=0.1*np.sign(B0)
            #if(sign(B0)*sign(B1)<0):
            #    B1=0.1*sign(B0)
            H_list[i][0]=round(np.sign(B0)*np.sqrt(Hz**2+B0**2),1)
            H_list[i][1]=round(np.sign(B1)*np.sqrt(Hz**2+B1**2),1)
            if(B1_temp*B0<0):
                H_list.insert(i,[2*np.sign(B1_temp),-2*np.sign(B1_temp),3])
            B1_temp=B1


        return H_list
    def AHE_with_Hz(self):
        #测量电阻随磁场的变化，如AHE、PHE
        self.init_common()
        self.link_ins(ins=['2182A','F1208高斯计','KEPCO电流源','GCD0301M'])#连接仪器
        self.link_ins_or(ins=['6221','2611A'])#根据实际连接选择电流源
        #self.B_Magnet_list=self.creat_H_list(H_list=self.B_Magnet_list,Hz=self.Hz)
        self.init_set_i_Magnet_list()
        Hz=self.Hz
        #预处理，第一个点有跳动，测两次
        self.set_i_Magnet(self.i_Magnet_list[0])
        B=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场和电阻
        if self.if_DC:
            self.set_i_DC(i_output=self.i_mea)
        R=self.mea_V()/self.i_mea
        self.sum_angle=0
        try:
            for i in range(self.loop_time):
                for i_Magnet in self.i_Magnet_list:
                    self.set_i_Magnet(i_Magnet)
                    #if(self.i_count>=len(self.i_Magnet_list)//2-1):
                    #    Hz=self.Hz*-1
                    H=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场和电阻
                    if(abs(self.Hz)<abs(H)):
                        print('第{}次测量'.format(self.i_count))
                        theta=np.arcsin(Hz/H)#总共要转动的角度
                        theta_rot=theta*180/np.pi-self.sum_angle#要转动角度
                        if(True):#abs(theta_rot)>0.1):
                            print('磁场大小为',H,'要转动角度为',theta_rot,'现在角度为',self.sum_angle)
                            self.SMR_update(theta_rot,if_save_data=0)
                        
                        H=H*np.cos(self.sum_angle/180*np.pi)
                        if self.if_DC:
                            R=self.mea_V()/self.i_mea#self.mea_R(i_output=self.i_mea)
                        else:
                            R=self.mea_R(i_output=self.i_mea)
                        self.i_count+=1
                        self.data.append([H,R])
                        print('励磁电流:{:g},磁场分量为:{:.4f},电阻:{:.8e}\n'.format(i_Magnet,H,R))  
                    else:
                        print('磁场大小为',H,'小于Hz,不记录数据')
                        theta=np.sign(Hz/H)*np.pi/2#总共要转动的角度
                        theta_rot=theta*180/np.pi-self.sum_angle#要转动角度
                        print('磁场大小为',H,'要转动角度为',theta_rot,'现在角度为',self.sum_angle)
                        self.SMR_update(theta_rot,if_save_data=0)
                self.save_data(self.data)
            t=time.time()-self.time
            print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))
            print('已转动{}°,结束返回初始位置中'.format(self.sum_angle))
            self.SMR_update(angle=-self.sum_angle,if_exit=0,if_save_data=0)
        except Exception as e:
            print('中途停止，原因',e)
            if(self.sum_angle!=0):
                print('中途停止,已转动{}°,结束返回初始位置中'.format(self.sum_angle))
                self.SMR_update(angle=-self.sum_angle,if_exit=0)
            assert 0   
        self.loop=0
    def mea_R_by_time(self):
        #在设定时间节点后同时测量R1,R2
        time_list=self.creat_list(self.time_list,'时间')
        self.link_ins(['6221'])  
        self.pulse_mea_R_cus(time_list,i_pulse=self.i_pulse,i_mea=self.i_mea,i_pulse_width=self.i_pulse_width,V_range=self.V_range)
        self.save_data(data=self.data)
        self.loop=0
    '''热测量相关'''
    def ANE(self):
        #能斯特 加热并等待稳定,设定磁场，开始测量
        self.link_ins(ins=['2182A','F1208高斯计','KEPCO电流源'])#连接仪器
        self.link_ins_or(ins=['6221','2611A'])#根据实际连接选择电流源
        self.heat(self.i_heat,t_wait=self.t_heat)
        if(True):
            #保存加热时候的数据
            self.save_data(self.data,attach_name='+heat_data',xlabel='t (s)',ylabel='V_sample (V)',data_header='tiems(n) V_sample(V) V_Pt100(V)')
        self.init_common()
        self.init_set_i_Magnet_list()
        for i in range(self.loop_time):
            self.set_i_Magnet(self.i_Magnet_list[0])
            V=self.mea_V()
            for i_Magnet in self.i_Magnet_list:
                self.set_i_Magnet(i_Magnet)#设定磁场
                B=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场
                V=self.mea_V()
                self.data.append([B,V])
        self.save_data(data=self.data)#保存数据
        self.loop=0
    '''五、设定磁场，旋转角度，测量电阻'''
    def creat_angle_list(self,angle_list_raw):
        #返回角度差列表
        angle_list=self.creat_list(angle_list_raw)
        #角度列表转换为角度差
        angle_list_temp=[angle_list[i+1]-angle_list[i] for i in range(len(angle_list)-1)]
        angle_list=[angle_list[0]]+angle_list_temp
        return angle_list
    def SMR_update(self,angle,if_save_data=1,if_exit=0):
        #旋转一定角度，测量电阻

        angle_real=self.rotation(angle=angle,speed=self.speed,subdivision=self.subdivision,if_exit=if_exit)
        self.sum_angle+=angle_real#更新现在的角度
        #print(self.wait_time_angle*angle/5*self.subdivision/2)
        self.rsleep(0.2)
        print('已转动{}°'.format(self.sum_angle))
        if(if_save_data):
            #测量电阻
            R=self.mea_R(i_output=self.i_output)
            self.data.append([self.sum_angle,R])
    def AHE_rot(self):
        #转角AHE
        try:
            self.init_common()
            rot_one=False#是否单次旋转模式
            self.sum_angle=0#角度累计归零
            #角度列表转化为每次运行的列表
            angle_list=self.creat_list(self.angle_list,'角度')
            if(len(angle_list)==0):
                print('角度列表为空,直接退出')
                return 0
            elif(len(angle_list)==1):
                print('仅旋转模式')
                rot_one=True
                self.link_ins(['GCD0301M'])
                angle_real=self.SMR_update(angle=angle_list[0],if_save_data=0)
                print('成功旋转%g°'%angle_real)
                self.loop=0
                return 0

            self.link_ins(ins=['2182A','F1208高斯计','KEPCO电流源','GCD0301M'])#连接仪器
            self.link_ins_or(ins=['6221','2611A'])#根据实际连接选择电流源
            angle_list=self.creat_angle_list(self.angle_list)


            self.init_set_i_Magnet_list()
            for angle in angle_list:
                #每转一定角度，测量一次AHE
                self.check_quit()
                self.init_common()
                self.SMR_update(angle,if_save_data=False)
                self.attach_name='+angle_%i°'%self.sum_angle
                print('当前角度%i°'%self.sum_angle)
                self.R_H(i_Magnet_list=self.i_Magnet_list)
                self.display_s='angle:%i°'%self.sum_angle
                t=time.time()-self.time
                print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))

            t=time.time()-self.time
            print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))
            print('已转动{}°,结束返回初始位置中'.format(self.sum_angle))
            self.SMR_update(angle=-self.sum_angle,if_exit=0,if_save_data=0)

            self.loop=0
        except Exception as e:
            print('中途停止，原因',e)
            if(self.sum_angle!=0 and rot_one==False):
                print('中途停止,已转动{}°,结束返回初始位置中'.format(self.sum_angle))
                self.SMR_update(angle=-self.sum_angle,if_exit=0)
            assert 0   
    '''其他'''
    def update_inf(self,func):
        '''返回能循环更新数据，直至loop被设为0的函数'''
        def wrapper(*args, **kw):
            self.init_common()
            try:
                while(self.loop):
                    if(len(self.data)>5000):
                        #测量超过5000次，停止测量
                        self.rexit()
                    func(*args, **kw)
                    time.sleep(self.wait_time)
            except AssertionError as e:
                print('检测到退出标志,程序退出中')
                if(str(e)):
                    print('细节：',e)
                if(len(self.data)>0):
                    self.save_data(data=self.data)
            except Exception as e:
                print('出现错误，程序退出中')
                print('细节：',e)
                if(len(self.data)>0):
                    self.save_data(data=self.data)
            self.rexit()
            t=time.time()-self.time
            print('时间已经过去 %.0f 分  %.0f 秒'%(t//60,t%60))
        return wrapper
    def start_inf(self,func):
        '''以新线程开始上面的函数，返回函数'''
        def wrapper(*args, **kw):
            self.thread = threading.Thread(target=self.update_inf(lambda:func(*args,**kw)))
            self.thread.start()
        return wrapper
    def start_new_thread_quickly(self,func):
        '''以新线程开始上面的函数，马上执行'''
        self.thread = threading.Thread(target=self.update_inf(func))
        self.thread.start()
    def start_new_thread(self,func):
        '''以新线程开始上面的函数，马上执行'''
        self.thread = threading.Thread(target=func)
        self.thread.start()
if __name__=='__main__':
    pass
   





