# -*- coding: utf-8 -*-
from cgi import test
from lib2to3.pgen2.tokenize import TokenError
import sys,time,os
import threading
from turtle import towards
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
        self.n_average=50 #多次测量，取平均值次数
        #励磁电源部分
        self.i_Magnet_min=-4.4 #0.08 #磁铁加的最小电流
        self.i_Magnet_max=4.4 #0.06 #磁铁加的最大电流
        self.n_Magnet=40 #磁铁从最小电流到最大电流之间点的数目  #细扫40个点
        self.i_Magnet_list_fine=[[-5.5,-5.3,3],[5.3,5.5,3]] #细扫
        self.B_Magnet_list=[[-100,100,30],[100,-100,30]]
        #self.ratio=9.1  #励磁电源电压与电流的比值，不能超过12,已弃用，电压改为加到最大值

        #纵向电流部分
        self.i_output=0.2e-3  #纵向输出电流，单位A
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

        #正负脉冲测量
        self.n_pulse_half_cycle=2 #半个周期内脉冲数
        self.n_mea_after_pulse=2 #一个脉冲后测量几个点
        #扫辅助场和辅助电流
        self.i_B_list=[0.038,0.4,0.9,1.3]
        self.i_output_list=[10e-3,20e-3,30e-3,50e-3,70e-3]   
        #谐波
        self.harm=1#谐波次数
        self.i_harm_list=[0.0005,0.001,0.0015] #正弦电流有效值
        self.freq=1333
        #SMR相关
        self.i_Magnet=1
        self.i_Magnet_list=1
        self.toward=0#旋转方向 0:角度增加 1:角度减少
        self.speed=150#旋转速度
        self.angle_one=5 #单次旋转的角度
        self.subdivision=2 #细分数
        self.sum_angle=0 #角度累计
        self.wait_time_angle=1.5 #每次转动后的等待时间
        self.angle_list=[[0,360,73]]
        #辅助参数
        self.wait_time=0.3  #一些要等待的地方的等待时间
        self.wait_time_DC=30
        self.thread=False #用于存放多线程
        self.error=1.3   
        self.t_heat=120
    
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
            ratio=1
            if(True):
                self.set_i_Magnet(-1)
                B1=self.mea_B_exact()
                self.set_i_Magnet(-0.5)
                B2=self.mea_B_exact()
                ratio=min(1000/abs(B2-B1),8)    
                print('比例系数为',ratio)    
            for B_range in B_Magnet_list:        
                if(B_range[0]==B_temp):
                    #如果两个区间交界处磁场一样，不重复定值
                    I_start=I_temp
                else:
                    I_start=self.set_B_Magnet(B_range[0],if_exact=0,error=2,ratio_space=ratio)[1]   
                I_stop=self.set_B_Magnet(B_range[1],if_exact=0,error=2,ratio_space=ratio)[1]  
                B_temp=B_range[1]    
                I_temp=I_stop                       
                i_Magnet_list.append([I_start,I_stop,B_range[2]])
            self.i_Magnet_list=self.creat_list(i_Magnet_list,name='励磁电流',if_loop=0)   

    '''一、改变磁场，测量电阻，如反常霍尔'''
    def AHE_update_one(self,loop_time=-100):
        '''反常霍尔测量更新数据用，设定好励磁电流后，测量磁场和电阻'''
        if(loop_time==-100):
            loop_time=self.loop_time
        if(self.i_count==0):
            #第一次测量之前，先连接仪器
            self.link_ins(ins=['2182A','F1208高斯计','KEPCO电流源'])
            self.link_ins_or(ins=['6221','2611A'])
            self.set_i_range(self.i_output)
            #设定初始值
            self.init_set_i_Magnet_list()
            self.mea_B_exact(error=0.1)#第一个点有跳动，不保存
            self.mea_R(self.i_output)

        print('第{}次测量'.format(self.i_count))
        #print(self.data)
        if(loop_time==-100):
            loop_time=self.loop_time_AHE

        
        #设置励磁电流，测量磁场与电阻
        self.set_i_Magnet(self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)])#设置励磁电流
        B=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场和电阻
        R=self.mea_R(self.i_output)
        #B=self.mea_B()

        data=[B,R]
        print('励磁电流:{:g},磁场:{:.4g},电阻:{:.8e}'.format(self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)],data[0],data[1]))

        if(self.loop):
            #退出时测的数据有问题，不记录
            self.data.append(data) #保存测量到的数据
            self.i_count+=1

        if((loop_time>0 and self.i_count//len(self.i_Magnet_list)>=loop_time) or self.loop==0):
            #到达测量次数或者loop等于0，保存并退出
            self.save_data(data=self.data,name=self.pre_name,xlabel=self.xlabel,ylabel=self.ylabel)
            self.loop=0
    def AHE_update(self,i_Magnet,i_output):
        #设置励磁电流，测量磁场与电阻
        self.set_i_Magnet(i_Magnet)#设置励磁电流
        B=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场和电阻
        R=self.mea_V()/i_output
        #B=self.mea_B()
        data=[B,R] 
        print('第{}次测量'.format(self.i_count))
        print('励磁电流:{:g},磁场:{:.4f},电阻:{:.8e}'.format(i_Magnet,data[0],data[1]))  
          
        self.data.append(data)   
        self.i_count+=1
    def AHE_sweep_i_output_DC(self):
        self.link_ins(ins=['2182A','F1208高斯计','KEPCO电流源'])
        self.link_ins_or(ins=['6221','2611A'])#根据实际连接选择电流源
        i_output_list=self.creat_list(self.i_output,name='测量直流电流')#设定测量电流列表
        self.init_set_i_Magnet_list()
        for i_output in i_output_list:

            self.set_i_range(abs(i_output))#设置量程
            #设定初始值
            self.init_common()
            self.set_i_DC(i_output=i_output)#设定测量电流
            self.mea_B_exact(error=0.1)#第一个点有跳动，不保存
            self.attach_name='+DC+{:g}mA'.format(i_output*1000)
            if(abs(i_output)>=4e-3):
                print('%gs后进行测量'%self.wait_time_DC)
                self.rsleep(self.wait_time_DC)
            for n in range(self.loop_time):
                for i_Magnet in self.i_Magnet_list:
                    self.AHE_update(i_Magnet,i_output)
            self.save_data(self.data)
            t=time.time()-self.time
            print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))
        self.loop=0
    def I_B(self,loop_time=-100):
        '''得到每个励磁电流对应的磁场'''
        if(loop_time==-100):
            loop_time=self.loop_time
        if(self.i_count==0):
            #第一次测量之前，先连接仪器
            self.link_ins(ins=['F1208高斯计','KEPCO电流源'])
            #设定初始值
            self.init_set_i_Magnet_list()
            self.mea_B_exact(error=0.1)#第一个点有跳动，不保存

        print('第{}次测量'.format(self.i_count))
        
        #设置励磁电流，测量磁场与电阻
        i_Magnet=i_Magnet=self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)]
        self.set_i_Magnet(i_Magnet)#设置励磁电流
        B=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场

        data=[i_Magnet,B]
        print('励磁电流:{:g},励磁电流:{:.4f}A,磁场:{:.4f}Oe'.format(self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)],data[0],data[1]))

        if(self.loop):
            #退出时测的数据有问题，不记录
            self.data.append(data) #保存测量到的数据
            self.i_count+=1

        if((loop_time>0 and self.i_count//len(self.i_Magnet_list)>=loop_time) or self.loop==0):
            #到达测量次数或者loop等于0，保存并退出
            self.save_data(data=self.data,name=self.pre_name,xlabel=self.xlabel,ylabel=self.ylabel)
            self.loop=0       
    '''二、设定磁场，加上脉冲电流，之后测电阻，如测量电流翻转过程'''
    def switch_loop_update_pulse(self,i_pulse,i_pulse_width,i_pulse_gap_time=2):
        '''脉冲电流回线测量用，加一个给定脉冲，i_pulse_gap_time后测量，最后返回给定的脉冲电流与测得的电阻'''

        #加上给定大小的脉冲
        print('*'*5,'开始加脉冲','*'*5)
        self.set_i_pulse(i_output=i_pulse,i_pulse_width=i_pulse_width)
        #一定时间后测量
        self.rsleep(i_pulse_gap_time)
        print('*'*5,'开始测量','*'*5)
        R2=self.mea_R(i_output=self.i_output)  

        self.i_count+=1
        return [i_pulse,R2]
    def switch_up_down_i_update(self,i_pulse,i_pulse_width,n_time=100):
        '''switch更新一次数据用，脉冲测量'''
        if(n_time==100):
            n_time=self.n_mea_after_pulse
        #加上给定大小的脉冲
        print('*'*5,'开始加脉冲','*'*5)
        self.set_i_pulse(i_output=i_pulse,i_pulse_width=i_pulse_width)

        #开始测量
        print('*'*5,'开始测量','*'*5)
        self.rsleep(self.i_pulse_gap_time)
        for i in range(self.n_mea_after_pulse):
            self.rsleep(1)
            R2=self.mea_R(i_output=self.i_output)
            self.data.append([self.i_count+1,R2])
            self.i_count+=1

    def switch_pulse_up_down_i(self,B_Magnet_assist,if_init=1,i_pulse=1e-3,n_pulse=100,if_exit=0):
        '''正负脉冲电流,刚开始几个零脉冲的点，之后几个周期的正负脉冲'''
        if(n_pulse==100):
            n_pulse=self.loop_time
        if(if_init):
            if(self.link_ins(ins=['6221','2182A','F1208高斯计','KEPCO电流源'])==-1):
                return -1
        #初始参数设置，如设置保存时的文件名
        self.init_common()

        #开始正式测量
        self.set_B_Magnet(B_target=B_Magnet_assist,error=1)
        B_Magnet_real=self.mea_B_exact(0.2)
        if(abs(B_Magnet_assist)<100):
            #小于100Oe时精度是0.1Oe，大于100的是1Oe
            self.attach_name='+set_%gOe+real_%gOe+%gmA+%gms'%(round(B_Magnet_assist,1),round(B_Magnet_real,1),round(i_pulse*1000,2),self.i_pulse_width*1000)
        else:
            self.attach_name='+set_%gOe+real_%gOe+%gmA+%gms'%(round(B_Magnet_assist,0),round(B_Magnet_real,0),round(i_pulse*1000,2),self.i_pulse_width*1000)    
        self.attach_name=self.attach_name+'+{:g}pulse_{:g}measuring'.format(self.n_pulse_half_cycle,self.n_mea_after_pulse)



        #初始几个点不加脉冲,看初始态怎么样
        self.switch_up_down_i_update(i_pulse=0,i_pulse_width=self.i_pulse_width,n_time=self.n_pulse_half_cycle*self.n_mea_after_pulse//2)

        for j in range(n_pulse):
            print('开始第{}个循环'.format(j))
            for k in range(self.n_pulse_half_cycle):
                self.switch_up_down_i_update(i_pulse=i_pulse,i_pulse_width=self.i_pulse_width)
            for k in range(self.n_pulse_half_cycle):
                self.switch_up_down_i_update(i_pulse=-i_pulse,i_pulse_width=self.i_pulse_width)                    
                                             
        #保存数据
        self.save_data(data=self.data)
        t=time.time()-self.time
        print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))
        if(if_exit):
            self.rexit()

    def creat_switch_loop_list(self):
        #设置扫描电流列表
        if(type(self.n_pulse) in [int,float]):
            self.n_pulse=int(self.n_pulse)
            i_pulse_list_begin=np.linspace(0,self.i_pulse_min,7,endpoint=False)
            i_pulse_list=np.linspace(self.i_pulse_min,self.i_pulse_max,self.n_pulse-1,endpoint=False)
            i_pulse_list=np.append(i_pulse_list,np.linspace(self.i_pulse_max,self.i_pulse_min,self.n_pulse))
            print('扫描电流列表为',i_pulse_list)
        elif(type(self.n_pulse) == list):
            i_pulse_list=self.creat_list(self.n_pulse,'扫描电流列表',if_loop=0)
            i_pulse_list_begin=np.linspace(0,i_pulse_list[0],7,endpoint=False)[1:]
            #print('扫描电流列表为',i_pulse_list)
        else:
            print(self.n_pulse)
            input('输入的脉冲数目格式不正确')
            self.loop=0
        return i_pulse_list_begin,i_pulse_list
    def switch_loop_i(self,B_Magnet_assist,if_init=1,if_exit=0,i_pulse_width=-100):
        '''脉冲电流回线测量'''
        if(i_pulse_width==-100):
            i_pulse_width=self.i_pulse_width
        self.init_common()
        #设置脉冲电流列表
        i_pulse_list_begin,i_pulse_list=self.creat_switch_loop_list()

        #设定辅助磁场
        self.set_B_Magnet(B_target=B_Magnet_assist,error=1)
        #设置文件名
        B_Magnet_real=self.mea_B_exact(0.2)
        if(abs(B_Magnet_assist)<101):
            #小于100Oe时命名精度是0.1Oe，大于100的是1Oe
            self.attach_name='+set_%gOe+real_%gOe+%gms+i_pulse_max_%gmA'%(round(B_Magnet_assist,1),round(B_Magnet_real,1),i_pulse_width*1000,max(i_pulse_list)*1000)
        else:
            self.attach_name='+set_%gOe+real_%gOe+%gms+i_pulse_max_%gmA'%(round(B_Magnet_assist,0),round(B_Magnet_real,0),i_pulse_width*1000,max(i_pulse_list)*1000)
        if(if_init):
            self.link_ins(ins=['6221','2182A','F1208高斯计','KEPCO电流源'])#连接仪器          
   
                    

        #开始初始翻转过程扫描（类似初始磁化曲线）
        if type(self.n_pulse) in [int,float]:
            for i in i_pulse_list_begin:
                data=self.switch_loop_update_pulse(i_pulse=i,i_pulse_width=i_pulse_width,i_pulse_gap_time=self.i_pulse_gap_time)
                if(self.loop):
                    self.data.append(data)
        #开始翻转过程扫描
        for j in range(self.loop_time):
            print('开始第{}个循环'.format(j+1))
            for i in i_pulse_list:
                data=self.switch_loop_update_pulse(i_pulse=i,i_pulse_width=i_pulse_width,i_pulse_gap_time=self.i_pulse_gap_time)
                if(self.loop):
                    self.data.append(data)

        #保存数据  
        self.save_data(data=self.data)
        t=time.time()-self.time
        print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))
        if(if_exit):
            self.rexit()
    def creat_pulse_up_down_list(self):
        #设置扫描电流列表
        if(type(self.n_pulse) in [int,float]):
            self.n_pulse=int(self.n_pulse)
            i_pulse_list=np.linspace(self.i_pulse_min,self.i_pulse_max,self.n_pulse,endpoint=True)
            print('扫描电流列表为',i_pulse_list)
        elif(type(self.n_pulse) == list):
            i_pulse_list=self.creat_list(self.n_pulse,'扫描电流列表')
            #print('扫描电流列表为',i_pulse_list)
        else:
            print(self.n_pulse)
            input('输入的脉冲数目格式不正确')
            self.loop=0
        return i_pulse_list
    def switch_sweep_B(self):
        #扫电流，扫描辅助场
        B_list=self.creat_list(self.B_Magnet_assist_list,name='辅助磁场')
        i_width_list=self.creat_list(self.i_pulse_width,name='脉冲宽度')

        self.link_ins(ins=['2182A','F1208高斯计','KEPCO电流源'])
        self.link_ins_or(ins=['6221','2611A'])#根据实际连接选择电流源
        for B in B_list:
            #扫描磁场
            for i_width in i_width_list:
                #扫描脉冲宽度
                self.i_pulse_width=i_width
                if(self.n_func==0):
                    #翻转电流回线测量
                    self.switch_loop_i(B_Magnet_assist=B,if_init=0,if_exit=0)
                elif(self.n_func==1):
                    i_pulse_list=self.creat_pulse_up_down_list()
                    for i_pulse in i_pulse_list:
                        #正负脉冲扫描电流
                        self.switch_pulse_up_down_i(B_Magnet_assist=B,if_init=0,i_pulse=i_pulse)
        self.loop=0        
    '''四、设定磁场，测量一次、二次谐波'''
    def harm_update_one(self,loop_time=-100,freq=133):
        '''一、二次谐波测量更新数据用，设定好励磁电流后，以及正弦电流后，测量磁场和一、二次谐波电压，正弦电流使用的是有效值'''
        if(loop_time==-100):
            loop_time=self.loop_time
        if(self.i_count==0):
            #第一次测量之前，先连接仪器
            self.link_ins(ins=['6221','SR830_1','F1208高斯计','KEPCO电流源'])
            #设定初始值
            self.init_set_i_Magnet_list()
            #仪器初始设定，包括输出正弦波
            self.set_i_SIN(freq=freq,i_AMPL=self.i_output*np.sqrt(2))
            #初始化SR830的设置
            self.init_HARM_com(HARM=self.harm)     
            time.sleep(3)#等待3s   

        print('第{}次测量'.format(self.i_count))
        
        #设置励磁电流，测量磁场与电阻
        self.set_i_Magnet(self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)])#设置励磁电流
        B=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量得到磁场
        V_w=self.mea_V_HARM(n_average=self.n_average)
        data=[B,V_w/self.i_output]
        print('磁场:{:.4f},霍尔电阻:{:.8e}'.format(data[0],data[1]))

        self.data.append(data) #保存测量到的数据
        self.i_count+=1

        if(loop_time>0 and (self.i_count//len(self.i_Magnet_list)>=loop_time)):
            #到达测量次数或者loop等于0，保存并退出
            self.save_data(data=self.data,name=self.pre_name,attach_name=self.attach_name,xlabel=self.xlabel,ylabel=self.ylabel)
            self.loop=0
            return 0
    def harm_togather_update(self,B_Magnet=0,n_average=5):
        '''一、二次谐波测量更新数据用，设定好励磁电流后，以及正弦电流后，测量磁场和一、二次谐波电压，正弦电流使用的是有效值'''
   
        print('第{}次测量'.format(self.i_count))
        
        #设置励磁电流，测量磁场
        self.set_i_Magnet(B_Magnet)#设置励磁电流
        B=self.mea_B_exact(error=self.error,wait_time=self.wait_time)  #测量稳定磁场

        #测量得到电压
        V=self.mea_V_HARM_togather(n_average=self.n_average)
        data=[B,V[0],V[1],V[2],V[3]]

        print('磁场:{:.4f},一次电压:{:.6e}，二次电压{:.6e}'.format(data[0],data[1],data[3]))
        self.data.append(data) #保存测量到的数据
        self.i_count+=1

    def loop_i_harm_togather(self):
        i_list=self.creat_list(self.i_harm_list,'二次谐波扫描电流')
        self.link_ins(ins=['6221','SR830_1','F1208高斯计','KEPCO电流源','SR830_2'])
        self.init_set_i_Magnet_list()
        self.init_HARM_com_togather()     
        time.sleep(3)#等待3s
        for i in i_list:
            #扫描电流
            self.init_common()
            self.attach_name='+{}mA'.format(i*1000)
            self.set_i_SIN(freq=self.freq,i_AMPL=i*np.sqrt(2))
            if(not self.is_auto_range_1 or (not self.is_auto_range_2)):
                input('手动调整好锁相的量程后按回车键继续')
                self.data_header='H(Oe) X1(V) Y1(V) X2(V) Y2(V)'
            for j in range(self.loop_time):
                #一条曲线多测几遍
                for B in self.i_Magnet_list:
                    self.harm_togather_update(B_Magnet=B,n_average=self.n_average)
            self.save_data(data=self.data)
        self.loop=0
    def harm_rotation(self):
        #转角二次谐波
        try:
            i_list=self.creat_list(self.i_harm_list,'二次谐波扫描电流')
            B_list=self.creat_list(self.B_Magnet_assist_list,'外加磁场')
            angle_list=self.creat_angle_list(self.angle_list)
            self.link_ins(ins=['GCD0301M','6221','SR830_1','F1208高斯计','KEPCO电流源','SR830_2'])   
            self.init_HARM_com_togather()#初始化两台锁相 
            for i_sin in i_list:
                self.sum_angle=0#角度累计归零
                self.attach_name='+{}mA+'.format(i_sin*1000)
                self.set_i_SIN(freq=self.freq,i_AMPL=i_sin*np.sqrt(2))
                if(not self.is_auto_range_1 or (not self.is_auto_range_2)):
                    input('手动调整好锁相的量程后按回车键继续')
                    self.data_header='H(Oe) X1(V) Y1(V) X2(V) Y2(V)'
                for B_Magnet in B_list:
                        self.init_common()
                        if(B_list[0]<0 and B_list[0]>-5.5):
                            #小于零时为设置励磁电流模式
                            print('此时为设置励磁电流模式')
                            self.set_i_Magnet(abs(B_Magnet))
                            B_Magnet_real=self.mea_B_exact()
                            self.attach_name='+%gmA+real_%gOe+HARM_rotation'%(i_sin*1000,round(B_Magnet_real,1))
                        else:
                            self.set_B_Magnet(B_Magnet)
                            B_Magnet_real=self.mea_B_exact()
                            self.attach_name='+%gmA+set_%gOe+real_%gOe+HARM_rotation'%(i_sin*1000,round(B_Magnet,1),round(B_Magnet_real,1))
                    
                        for angle in angle_list:
                            #每转一定角度，测量一次电阻
                            self.rsleep(self.wait_time_angle)
                            self.SMR_update(angle=angle,if_save_data=0)
                            #测量得到电压
                            V=self.mea_V_HARM_togather(n_average=self.n_average)
                            data=[self.sum_angle,V[0],V[1],V[2],V[3]]

                            print('一次电压:{:e}，二次电压{:e}'.format(data[0],data[1],data[3]))
                            self.data.append(data) #保存测量到的数据

                        self.save_data(data=self.data)#保存数据
                        #为了防止线损坏，转回初始位置
                        t=time.time()-self.time
                        print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))
                        print('已转动{}°,结束返回初始位置中'.format(self.sum_angle))
                        self.SMR_update(angle=-self.sum_angle,if_exit=0,if_save_data=0)        
            self.loop=0
        except:
            if(self.sum_angle!=0):
                print('中途停止,已转动{}°,结束返回初始位置中'.format(self.sum_angle))
                self.SMR_update(angle=-self.sum_angle,if_exit=0)
            assert 0  
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
    def SMR(self):
        #转角测电阻
        try:
            self.init_common()
            rot_one=False#是否单词旋转模式
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

            #设置磁场
            if self.B_Magnet_assist_list!='None':
                #在给定磁场的情况下设定磁场
                B_Magnet_list=self.creat_list(eval(self.B_Magnet_assist_list),'磁场')
                for B_Magnet in B_Magnet_list:
                    self.init_common()
                    self.sum_angle=0#角度累计归零
                    self.set_B_Magnet(B_Magnet)
                    B_Magnet_real=self.mea_B_exact()
                    self.attach_name='+set_%gOe+real_%gOe'%(round(B_Magnet,1),round(B_Magnet_real,1))
                    for angle in angle_list:
                        #每转一定角度，测量一次电阻
                        self.rsleep(self.wait_time_angle)
                        self.SMR_update(angle)

                    self.save_data(data=self.data)#保存数据
                    #为了防止线损坏，转回初始位置
                    t=time.time()-self.time
                    print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))
                    print('已转动{}°,结束返回初始位置中'.format(self.sum_angle))
                    self.SMR_update(angle=-self.sum_angle,if_exit=0,if_save_data=0)
                    

            else:
                print('进入设置励磁电流模式')
                i_Magnet_list=self.creat_list(self.i_Magnet_list,'励磁电流')
                for i_Magnet in i_Magnet_list:
                    self.init_common()
                    self.sum_angle=0#角度累计归零
                    self.set_i_Magnet(i_Magnet)#加磁场
                    B_Magnet_real=self.mea_B_exact()#等待磁场稳定后开始测量
                    self.attach_name=self.attach_name='+real_%gOe'%(round(B_Magnet_real,1))
                    for angle in angle_list:
                        #每转一定角度，测量一次电阻
                        self.SMR_update(angle)

                    self.save_data(data=self.data)#保存数据
                    #为了防止线损坏，转回初始位置
                    t=time.time()-self.time
                    print('距离开始过去了{}分{:.2f}秒'.format(t//60,t%60))
                    print('已转动{}°,结束返回初始位置中'.format(self.sum_angle))
                    self.SMR_update(angle=-self.sum_angle,if_exit=0,if_save_data=0)

            self.loop=0
        except:
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
                    #t=time.time()
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
    test=measure()
    test.loop=1
    test.B_Magnet_assist_list=[-1,-5]
    test.harm_rotation()
   





