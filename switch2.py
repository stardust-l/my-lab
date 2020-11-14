# -*- coding: utf-8 -*-
import sys,time,os,time
import pyvisa as visa
import threading
import numpy as np
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tkinter import messagebox



class control(object):
    '''仪器控制
    属性：1.仪表名称以及所对应地址，2.ni-visa存放位置
    功能：1.设置输出电流，测量不同励磁电流下的电压值,把数据存放在列表中
    '''
    instruments={'2182A':'GPIB0::7::INSTR','2611A':'GPIB0::26::INSTR',
    'F1208高斯计':'ASRL7::INSTR','6221':'GPIB0::15::INSTR','KEPCO电流源':'GPIB0::6::INSTR'} #仪器及其所对应地址
    visa_dll = ''

    def __init__(self):
        self.rm='' 
        self.instruments_list=''
        self.ins={}  #用于存放已经连接的仪器


        #励磁电源部分
        self.i_Magnet_min=-5 #0.08 #磁铁加的最小电流
        self.i_Magnet_max=5 #0.06 #磁铁加的最大电流
        self.n_Magnet=40 #磁铁从最小电流到最大电流之间点的数目  #细扫40个点
        self.i_Magnet_list_fine=[[-6,-5,4],[-5,5,1],[5,6,4]] #细扫
        #self.ratio=9.1  #励磁电源电压与电流的比值，不能超过12,已弃用，电压改为加到最大值

        #纵向电流部分
        self.i_output=1e-3  #纵向输出电流，单位A
        self.width=50.0/1000 #纵向电流脉冲宽度

        #脉冲相关
        self.i_pulse_max=6e-3 #脉冲的最高值（-0.105到0.105A)
        self.i_pulse_min=-6e-3 #脉冲的最低值，还未启用
        self.i_pulse_width=1e-3 #脉冲宽度（0,0.001到999s）
        self.i_pulse_gap_time=10 #两次脉冲之间的间隔时间
        self.n_pulse=11 #脉冲总数目
        self.i_Magnet_assist=1#辅助磁场需要加的电流    
        self.B_Magnet_assist=100 #辅助场大小
        self.B_Magnet_assist_list=[10,50,100]
        self.loop_time=2#扫脉冲循环次数

        #扫辅助场和辅助电流
        self.i_B_list=[0.038,0.4,0.9,1.3]
        self.i_output_list=[10e-3,20e-3,30e-3,50e-3,70e-3]   
        
        #辅助参数
        self.wait_time=0.3  #一些要等待的地方的等待时间
        #self.n_average=2 #重复测量，取平均值的次数 ,暂时不用了

        self.thread=False #用于存放多线程
        self.start_time=time.time()
        self.time=0 #用于记录时间
        self.loop=1 #测量开始后作为停止判断，只有loop设为0的时候才停止测量
        self.data=[]  #用于存放读取来的数据
        self.i_count=0
        self.error=1.3



        self.if_AHE_pre=0 #翻转前是否测AHE
        self.if_AHE_after=0 #翻转后是否测AHE

        #文件存储路径
        self.pre_name='1#'
        self.file_name='Newfile'
        self.attach_name=''
        self.fold='data'

    def initialization(self):
        '''
        1.参数初始化，包括励磁电流表
        2.仪器初始化，包括连接各仪器，设置停止位，重置各仪器等
        '''

        #生成励磁电流列表
        if(self.n_Magnet or not self.i_Magnet_list_fine):
            self.i_Magnet_list=np.linspace(self.i_Magnet_min,self.i_Magnet_max,self.n_Magnet)          
            self.i_Magnet_list=np.append(self.i_Magnet_list,self.i_Magnet_list[::-1])
        else:
            self.i_Magnet_list=np.array([])
            for i_list in self.i_Magnet_list_fine:
                self.i_Magnet_list=np.append(self.i_Magnet_list,np.linspace(i_list[0],i_list[1],i_list[2],endpoint=False))
            self.i_Magnet_list=np.append(self.i_Magnet_list,self.i_Magnet_list_fine[-1][-2])
            self.i_Magnet_list=np.append(self.i_Magnet_list,self.i_Magnet_list[::-1])
        #print('励磁电流列表为：',self.i_Magnet_list)

        #连接仪器资源
        try:
            self.visa_dll = 'c:/windows/system32/visa64.dll'
            self.rm=visa.ResourceManager(self.visa_dll)     
            self.instruments_list=self.rm.list_resources()
            print('目前已连接的仪器有：',self.instruments_list)
        except:
            print('无法找到ni-visa，停止测量')
            self.rexit()
            return -1

        for name in ['KEPCO电流源','6221']:
            #连接各仪器,并初始化
            try:
                print(self.instruments[name])
                self.ins[name]=self.rm.open_resource(self.instruments[name])
                self.ins[name].write('*RST')
                print('成功连接'+name)
            except:
                print(name+'无法连接，程序退出')
                self.rexit()
                return -1

        try:
            if(not int(self.ins['6221'].query('SOUR:PDEL:NVPR?'))):
                self.ins['2182A']=self.rm.open_resource(self.instruments['2182A'])
                self.ins['2182A'].write('*RST')
                print('成功连接2182A')
        except Exception as e:
            print('2182A无法连接，程序退出')
            print('Reason',e)
            self.rexit()
            return -1            
        try:
            self.ins['F1208高斯计']=self.rm.open_resource(self.instruments['F1208高斯计'])
            self.ins['F1208高斯计'].read_termination = '\r' #F1208高斯计返回的结束符是\r
            self.ins['F1208高斯计'].query('*RST\r')#初始化
            self.ins['F1208高斯计'].query('RANGES 0') #自动定量程
            print('成功连接高斯计')
        except:
            print('高斯计无法连接，程序退出')
            self.rexit()  
            return -1          
        #self.ins['6221'].write('CURRent {}'.format(self.i_output)) #设置输出电流
        self.ins['6221'].write('OUTPUT ON')#开始输出电流

        self.ins['KEPCO电流源'].clear() #清除寄存器，不加这个，电流源可能不响应
        self.ins['KEPCO电流源'].write('OUTPUT ON')  #开始输出
    '''一、设置磁场、脉冲'''
    def set_i_Magnet(self,i_Magnet,radio=12):
        #给励磁电流源加上要求的电流
        #确认输出电流
        #i_Magnet=self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)]
        if abs(i_Magnet)>6:
            #检测电流是否超过量程
            i_Magnet=6*i_Magnet/abs(i_Magnet)
            print('给定电流超过量程6A，已重设为6A')
            print("警告",'给定电流超过量程6A，已重设为6A')      
        if(radio>12):
            radio=12
        #设置励磁电流的输出
        self.ins['KEPCO电流源'].clear() #清除寄存器，不加这个，励磁电流源可能不响应
        self.ins['KEPCO电流源'].write('VOLT {:.5f};CURR {:.5f}'.format(i_Magnet*radio,i_Magnet))
        #print('励磁电流为'+'CURR {:.4f}'.format(i_Magnet))

    def pulse(self,i_output=2e-11,i_pulse_width=1e-3):
        '''用以输出脉冲'''
        if(i_output >1e-11 and i_output<3e-11):
            i_output=self.i_output
        self.ins['6221'].write('*RST')
        time.sleep(0.5)

        print('开始设置脉冲:','加的脉冲大小为{:.2f}mA,宽度为{:.2f}ms'.format(1000*i_output,1000*i_pulse_width))
        command=''#用以放置传给6221的命令
        command+='SOUR:SWE:SPAC LIST;SOUR:SWE:RANG AUTO;' #选择自定义模式；量程自动选择 2e-4
        command+='SOUR:LIST:CURR {},0;SOUR:LIST:DEL {},10e-3;SOUR:LIST:COMP 50,50;'.format(i_output,i_pulse_width)#设定脉冲电流大小（-0.105到0.105A);脉冲宽度（0.001到999s）;电压上限（0.1-105V）
        command+='SOUR:SWE:COUN 1;SOUR:SWE:CAB ON;'#循环次数一次;电压超限制后不停止
        command+='SOUR:SWE:ARM'#准备输出；开始输出脉冲
        for com in command.split(';'):
            self.ins['6221'].write(com)
        time.sleep(1)
        self.ins['6221'].write('INIT')
        #print('stat1',self.ins['6221'].query('*STB?'))
        time.sleep(1)
        #print(self.ins['6221'].query('CURR?'))
        #while(float(self.ins['6221'].query('CURR?'))>0.1*i_output):
        #print('stat2',self.ins['6221'].query('*STB?'))
        #self.ins['6221'].write('OUTP OFF')
        #self.ins['6221'].write('*RST')
        
        
        
        #input('')

    def set_B_Magnet(self,B_target,error=1.3):

        delta_B=B_target-self.mea_B_exact(error=20)#得到现在的磁场和目标磁场的偏差#现在磁场与目标磁场的差值

        self.ins['KEPCO电流源'].clear()
        I=float(self.ins['KEPCO电流源'].query('CURR?'))
        kp=0.85/2000#比例项系数
        radio=12
        print('目标磁场为:',B_target,'Oe',sep='')
        if(abs(B_target)<101):
            error=0.1
        while(abs(delta_B)>error):
            #sum_delta_B+=+delta_B_temp
            try:
                if(abs(delta_B)<2):
                    kp=0.2/2000
                if(abs(B_target)<101):
                    radio=2
                    kp=3/2000
                    error=0.1
                    time.sleep(2)
                if(self.loop==0):
                    return 0
                deltaI=sorted([kp*(delta_B),5e-5*abs(delta_B)/delta_B],key=abs)[-1]#用比例控制，得到要加的励磁电流 +sum_delta_B/10
                print('变化电流为：%.5fA'%deltaI,'距离目标磁场距离为：%.3fOe'%delta_B,sep='')
                print('现励磁电流为',I)
                self.ins['KEPCO电流源'].clear()
                I+=deltaI
                time.sleep(1)
                self.set_i_Magnet(I,radio)
                #time.sleep(min(1/abs(delta_B),0.2))
                delta_B=B_target-self.mea_B_exact(error=abs(delta_B)*0.1)
                if(self.loop==0):
                    self.rexit()
                
            except Exception as e:
                print('problem',e)
        print('设置完成，实际磁场为',-delta_B+B_target)
    '''二、测量单个物理量，磁场，电阻'''
    def mea_B(self):
        '''测量得到磁场'''
        B=self.ins['F1208高斯计'].query('FIELD?\r')#读取磁场

        count=3
        while(B=='+1E' or B=='-1E'):
            #超量程后重新读取
            time.sleep(self.wait_time)
            B=self.ins['F1208'].query('FIELD?\r')
            count-=1
            if(not count):
                print('高斯计一直超量程，退出程序')
                self.rexit()
        return float(B)
    def mea_B_exact(self,error=1,wait_time=''):
        '''测量得到磁场,等待磁场稳定'''
        if(not wait_time):
            wait_time=self.wait_time
        B1=1000
        while(True):
            B=self.ins['F1208高斯计'].query('FIELD?\r')#读取磁场
            if(error<0):
                error=-error
            count=3
            while(B=='+1E' or B=='-1E'):
                #超量程后重新读取
                time.sleep(wait_time)
                B=self.ins['F1208高斯计'].query('FIELD?\r')
                count-=1
                if(not count):
                    print('高斯计一直超量程，退出程序')
                    self.rexit()
            if(abs(B1-float(B))<error):
                #短时间变化小于一定值才停止测量
                return float(B)
            B1=float(B)
            time.sleep(self.wait_time)

    def pulse_mea_RH(self,i_output='',i_pulse_width=200e-6,if_absorb=0):
        '''加上脉冲，测量'''
        if(not i_output):
            i_output=self.i_output
        '''用默认1mA，200us的脉冲测量材料电阻'''
        if(if_absorb):
            self.ins['6221'].write('SOUR:SWE:ABOR')
            time.sleep(2)
        #print('ARM?',int(self.ins['6221'].query('PDELta:ARM?')))
        if(not int(self.ins['6221'].query('PDELta:ARM?'))):
            #not bool(self.ins['6221'].query('PDELta:ARM?'))
            #脉冲大小不变的操作  
            #电压上限(105v)，脉冲最高值(0.105)，最低值(-0.105)，宽度(50e-6到12e-3),2182A测量延时(16e-6到11.996e-3)
            #self.ins['6221'].write('*RST')
            print('开始设置脉冲:','加的脉冲大小为{:.2e},宽度为{:.2e}'.format(i_output,i_pulse_width))
            self.ins['6221'].write('*RST')
            time.sleep(2)#SOUR:PDEL:LME 0
            com='SOUR:PDEL:SWE OFF;CURR:COMP 60;SOUR:PDEL:HIGH {};SOUR:PDEL:LOW 0;SOUR:PDEL:LOW 0;SOUR:PDEL:WIDT {};SOUR:PDEL:SDEL {};'.format(i_output,i_pulse_width,i_pulse_width/2)

            #脉冲重复次数；脉冲间隔(5到999999)，例如5表示5个间隔，交流电为50Hz时，一个完整测量周期为5/50=100ms；2182A量程自动
            com+='SOUR:PDEL:COUN 1;SOUR:PDEL:INT 5;SYST:COMM:SER:SEND ":SENS:VOLT:RANGE 0.1";'#:AUTO ON

            #6221量程为最合适的;准备开始
            com+='SOUR:PDEL:RANG BEST;SOUR:PDEL:ARM'
            #开始Pulse Delta模式的测量
            for c in com.split(';'):
                self.ins['6221'].write(c)
            while(not int(self.ins['6221'].query('PDELta:ARM?'))):
                time.sleep(0.5)
            time.sleep(1)

        #读取6221数据,读取2182A的数据

        self.ins['6221'].write('INIT:IMM')
        time.sleep(1) #等待pulse delta测量结束
        
        V,I=list(map(float,self.ins['6221'].query('SENS:DATA?').split(',')))[:2]

        #停止测量
        print('测量电压为%.5e'%V,'未知数据%.5e'%I,'电阻为%.5e'%(V/i_output),sep=',')
        #self.ins['6221'].write('SOUR:SWE:ABOR')
        if(self.loop==0):
            self.ins['6221'].write('SOUR:SWE:ABOR')
            return V/i_output

        return V/i_output
    def mea_RH(self,ifrst=0):
        '''测量得到霍尔电阻，伪脉冲电流,减去背底热电压'''

        #测量电阻
        #self.ins['6221'].write('OUTP OFF')
        if(ifrst):
            self.ins['6221'].write('*RST')
            time.sleep(0.5)
        self.ins['6221'].write('OUTP ON')
        v_background1=float(self.ins['2182A'].query(":READ?"))#获取背底热电压
        self.ins['6221'].write('CURRent {}'.format(self.i_output)) #开始输出纵向电流
        time.sleep(self.width/2) #经过一段时间后开始测量电压
        meas_v=float(self.ins['2182A'].query(":READ?"))#获取电压
        time.sleep(self.width/2)
        self.ins['6221'].write('CURRent 0') #关闭电流源
        v_background2=float(self.ins['2182A'].query(":READ?"))#获取背底热电压

        return (meas_v-0.5*v_background1-0.5*v_background2)/(self.i_output)#计算得到电阻  


    '''翻转测量部分'''
    def switch_update_i_232(self,i_pulse,i_pulse_width):
        '''switch更新一次数据用，脉冲测量'''
        try:
            #加上给定大小的脉冲
            print('*'*5,'开始加脉冲','*'*5)
            R1=self.pulse_mea_RH(i_output=i_pulse,i_pulse_width=i_pulse_width,if_absorb=1)
            #6s后测量
            time.sleep(self.i_pulse_gap_time)
            print('*'*5,'开始测量','*'*5)
            R2=self.pulse_mea_RH(i_output=self.i_output,i_pulse_width=12e-3,if_absorb=1)
            time.sleep(1)
            print('\n')
        except Exception as e:
            print('测量出现问题，不记录数据')
            print('原因',e)
            return -1    
        self.data.append([i_pulse,R2])
        self.i_count+=1
    def switch_update_i(self,i_pulse,i_pulse_width,i_pulse_gap_time='none'):
        '''switch更新一次数据用，脉冲测量'''
        if(i_pulse_gap_time=='none'):
            i_pulse_gap_time=self.i_pulse_gap_time
        try:
            #加上给定大小的脉冲
            print('*'*5,'开始加脉冲','*'*5)
            self.pulse(i_output=i_pulse,i_pulse_width=i_pulse_width)
            #6s后测量
            time.sleep(i_pulse_gap_time)
            print('*'*5,'开始测量','*'*5)
            R2=self.mea_RH(ifrst=1)               
            time.sleep(1)
            print('\n')
        except Exception as e:
            print('测量出现问题，不记录数据')
            print('原因',e)
            return -1    
        self.data.append([i_pulse,R2])
        self.i_count+=1
    def switch_up_down_i_update(self,i_pulse,i_pulse_width,i_pulse_gap_time='none'):
        '''switch更新一次数据用，脉冲测量'''
        if(i_pulse_gap_time=='none'):
            i_pulse_gap_time=self.i_pulse_gap_time
        try:
            #加上给定大小的脉冲
            print('*'*5,'开始加脉冲','*'*5)
            self.pulse(i_output=i_pulse,i_pulse_width=i_pulse_width)
            #开始测量
            time.sleep(1)
            print('*'*5,'开始测量','*'*5)
            R2=self.mea_RH(ifrst=1)
            self.data.append([self.i_count,R2])
            self.i_count+=1
            for i in range(int(i_pulse_gap_time)):
                R2=self.mea_RH(ifrst=0)
                time.sleep(0.2)
                self.data.append([self.i_count,R2])
                self.i_count+=1
            print('\n')
        except Exception as e:
            print('测量出现问题')
            print('原因',e)
            return -1
    
        
        
    def switch_update_one_i_B(self):
        '''switch更新一次数据用，先加上辅助磁场，再给定脉冲电流'''   
        print('第{}次测量'.format(self.i_count))
        self.set_B_Magnet(self.B_Magnet_assist)#给电磁铁加上要求的电流
        
        while(time.time()-self.time<self.i_pulse_gap_time):
            #两次加脉冲过程中测量
            time.sleep(self.wait_time*0.2)
            try:
                #测量出现问题，不记录数据，开始下一次测量
                data=[self.mea_B_exact(self.error),self.mea_RH()] #测量得到磁场和电阻
            except Exception as e:
                print('测量出现问题，不记录数据')
                print('原因',e)
                return -1
            self.data.append([time.time()-self.start_time,data[1]])
            if(self.loop==0):
                #循环置为0时，尽快停止测量
                return 0
        self.time=time.time()
        self.pulse()#开始输出脉冲
        print('已加大小为{}A，宽度为{}s的脉冲'.format(self.i_pulse_max,self.i_pulse_width))
        self.i_pulse_max*=-1 #下次脉冲反向
        self.i_count+=1
    def switch_update_one(self):
        '''switch更新一次数据用，先加上辅助磁场，再给定脉冲电流'''   
        print('第{}次测量'.format(self.i_count))
        self.set_B_Magnet(self.B_Magnet_assist)#给电磁铁加上要求的电流
        
        while(time.time()-self.time<self.i_pulse_gap_time):
            #两次加脉冲过程中测量
            time.sleep(self.wait_time*0.2)
            try:
                #测量出现问题，不记录数据，开始下一次测量
                data=[self.mea_B_exact(0.1),self.mea_RH()] #测量得到磁场和电阻
            except Exception as e:
                print('测量出现问题，不记录数据')
                print('原因',e)
                return -1
            self.data.append([time.time()-self.start_time,data[1]])
            if(self.loop==0):
                #循环置为0时，尽快停止测量
                return 0
        self.time=time.time()
        self.pulse()#开始输出脉冲
        print('已加大小为{}A，宽度为{}s的脉冲'.format(self.i_pulse_max,self.i_pulse_width))
        self.i_pulse_max*=-1 #下次脉冲反向
        self.i_count+=1
    def switch_sweep_i(self,B='none',if_init=1,if_exit=1):
        self.loop=1
        self.data=[]
        self.i_count=0
        if(if_init):
            self.initialization()
        if(B=='none'):
            B=self.B_Magnet_assist

        try:
            if(self.loop==0):
                #循环置为0时，尽快停止测量
                return 0
            self.set_B_Magnet(B_target=B,error=1)

            if(self.loop_time>0):
                #设置保存路径
                s='sweep_i-%.0fOe-%.0fms'%(B,self.i_pulse_width*1000)
                self.attach_name='-'+s
                #设置扫描电流列表
                i_pulse_list_begin=np.linspace(0,self.i_pulse_max,self.n_pulse//2,endpoint=False)
                i_pulse_list=np.linspace(self.i_pulse_max,self.i_pulse_min,self.n_pulse-1,endpoint=False)
                i_pulse_list=np.append(i_pulse_list,np.linspace(self.i_pulse_min,self.i_pulse_max,self.n_pulse))
                #i_pulse_list=np.linspace(self.i_pulse_min,self.i_pulse_max,self.n_pulse)
                #i_pulse_list=np.append(i_pulse_list,i_pulse_list[-2::-1])
                print('扫描电流列表为',i_pulse_list)
                #开始初始翻转过程扫描（类似初始磁化曲线）
                for i in i_pulse_list_begin:
                    if(self.loop==0):
                        #循环置为0时，尽快停止测量
                        return 0
                    self.switch_update_i(i_pulse=i,i_pulse_width=self.i_pulse_width)
                #开始翻转过程扫描
                for j in range(self.loop_time):
                    print('开始第{}个循环'.format(j+1))
                    for i in i_pulse_list:
                        if(self.loop==0):
                            #循环置为0时，尽快停止测量
                            return 0
                        self.switch_update_i(i_pulse=i,i_pulse_width=self.i_pulse_width)
                    #保存数据
                    
                    self.save_data(name='-'+s,label=self.pre_name.strip('.txt')+'-'+s)
            else:
                i_pulse_list=np.linspace(self.i_pulse_min,self.i_pulse_max,self.n_pulse)
                print('扫描电流列表为',i_pulse_list)
                for i in i_pulse_list:
                    if(self.loop==0):
                        #循环置为0时，尽快停止测量
                        return 0
                    self.switch_up_down_i(B=B,if_init=0,i_pulse_max=i,n_pulse=-self.loop_time,if_exit=if_exit)
        except Exception as e:
            print('reason:',e)
            self.rexit()
        if(if_exit):
            self.rexit()
    def switch_up_down_i(self,B='none',if_init=1,i_pulse_max='none',n_pulse=15,if_exit=1):
        '脉冲电流'
        self.loop=1
        self.data=[]
        self.i_count=0
        if(if_init):
            self.initialization()
        if(B=='none'):
            B=self.B_Magnet_assist
        if(i_pulse_max=='none'):
            i_pulse_max=self.i_pulse_max

        s='%.0fOe-%.2fmA-%.0fms'%(B,i_pulse_max*1000,self.i_pulse_width*1000)
        self.attach_name='-'+s
        try:
            if(self.loop==0):
                #循环置为0时，尽快停止测量
                return 0
            self.set_B_Magnet(B_target=B,error=1)
            #i_pulse_list=np.linspace(self.i_pulse_min,self.i_pulse_max,self.n_pulse)
            #i_pulse_list=np.append(i_pulse_list,i_pulse_list[-2::-1])

            #开始翻转过程扫描
            self.switch_up_down_i_update(i_pulse=0,i_pulse_width=self.i_pulse_width)
            for j in range(n_pulse):
                print('开始第{}个循环'.format(j))
                if(self.loop==0):
                    #循环置为0时，尽快停止测量
                    return 0
                self.switch_up_down_i_update(i_pulse=i_pulse_max,i_pulse_width=self.i_pulse_width)
                self.switch_up_down_i_update(i_pulse=-i_pulse_max,i_pulse_width=self.i_pulse_width)
            #保存数据
            self.save_data(name='-'+s,label=self.pre_name.strip('.txt')+'-'+s)
        except Exception as e:
            print('reason:',e)
            self.rexit()
        if(if_exit):
            self.rexit()

    def switch_sweep_i_B(self):
        #扫电流，扫描辅助场
        B_list=self.creat_list(self.B_Magnet_assist_list,name='辅助磁场')
        self.loop=1
        self.data=[]
        self.i_count=0
        if(list(B_list)==-1):
            #发生错误不进行测量
            return -1
        self.initialization()
        for B in B_list:
            if(self.loop==0):
                return 0
            self.switch_sweep_i(B=B,if_init=0,if_exit=0)

    def creat_list(self,l,name=''):
        #根据输入的l，生成列表
        my_list=np.array([])
        if(type(l) in [float,int]):
            #输入的是单个数字
            my_list=[l]
        elif(type(l)==list):
            #输入的是列表
            if(type(l[0])==list and type(l[0][0]) in [int,float]):
                #输入的是一个二维列表
                if(len(l[0])!=3):
                    print('输入的必须是[[10,100,5],[100,500,7]]的形式，括号内要有三个数')
                    return -1
                for my_list_define in l:
                    my_list=np.append(my_list,np.linspace(my_list_define[0],my_list_define[1],my_list_define[2],endpoint=False))
                my_list=np.append(my_list,l[-1][-2])
            elif(type(l[0]) in [float,int]):
                #输入的是一维列表
                my_list=l
            else:
                print('输入格式有误，重新输入')
                return -1
        else:
            print('输入格式有误，重新输入')
            return -1
        print(name,'列表为',my_list,sep='')
        return my_list
    '''霍尔测量部分'''
    def AHE_update_one(self):
        '''反常霍尔测量更新数据用，设定好励磁电流后，测量磁场和电阻'''
        print('第{}次测量'.format(self.i_count))
        #print(self.data)
        self.set_i_Magnet(self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)])#设置励磁电流

        try:
            #测量出现问题，不记录数据，开始下一次测量
            if(not int(self.ins['6221'].query('SOUR:PDEL:NVPR?'))):
                R=self.mea_RH()
            else:
                R=self.pulse_mea_RH(self.i_output,i_pulse_width=10e-3)
            data=[self.mea_B_exact(error=self.error),R]  #测量得到磁场和电阻
            print('磁场:{:.4f},电阻:{:.8e}'.format(data[0],data[1]))
        except Exception as e:
            print('测量出现问题，不记录数据')
            print('原因',e)
            return -1
        #data=[self.mea_B_exact(10),self.mea_RH()]  #测量得到磁场和电阻
        self.data.append(data)
        self.i_count+=1

    def plot_B_i(self):
        '''以确定励磁电流和磁场的关系'''
        self.initialization()
        i_B=np.linspace(-6,6,60)
        i_B=np.append(i_B,i_B[-2::-1])
        


    def save_data(self,name='',label='',pre_name='none',fold='none'):
        '''保存现有的数据的txt文件，以及绘图，保存成png'''
        if(pre_name=='none'):
            pre_name=self.pre_name
        if(fold=='none'):
            fold=self.fold 
        if('.txt' in self.pre_name):
            self.pre_name=self.pre_name[:-4]
        if not os.path.exists(self.fold):
            os.makedirs(self.fold)
        print('保存到'+self.fold+'/'+self.pre_name+name+'.txt')
        np.savetxt(self.fold+'/'+self.pre_name+name+'.txt',self.data)
        x=[x[0] for x in self.data]
        y=[y[1] for y in self.data]
        plt.plot(x,y,'ro-',label=label)
        plt.legend(loc='best',frameon=False)

        ax = plt.gca()
        ax.minorticks_on()#显示次刻度线
        ax.yaxis.get_major_formatter().set_powerlimits((0,1))#设置纵轴刻度为科学计数法

        plt.grid(b=True, which='major', lw='0.5', linestyle='-')
        plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        
        

        if not os.path.exists(self.fold+'/fig'):
            os.makedirs(self.fold+'/fig')

        plt.savefig(self.fold+'/fig/'+self.pre_name+name+'.png')
        plt.close()


    #设置能循环更新的函数      
    def update_inf(self,func):
        '''返回能循环更新数据，直至loop被设为0的函数'''
        def wrapper(*args, **kw):
            self.loop=1
            self.data=[]
            self.i_count=0
            self.initialization()
            while(self.loop):
                if(len(self.data)>5000):
                    #测量超过5000次，停止测量
                    self.rexit()
                #t=time.time()
                func(*args, **kw)
                time.sleep(self.wait_time)
                #print(self.i_count,time.time()-t) 
            self.rexit()
        return wrapper
        
       

    def updata_test_one(self):
        '''测试用，利用随机数来更新数据'''
        self.data.append([self.i_count,random.uniform(1,5)])
        self.i_count+=1  

    def get_data(self):
        #返回数据
        return self.data   
    
    def start_inf(self,func):
        '''开始测量'''
        def wrapper(*args, **kw):
            self.thread = threading.Thread(target=self.update_inf(lambda:func(*args,**kw)))
            self.thread.start()
        return wrapper
        
         
    def start(self,func):
        '''开始测量'''
        def wrapper(*args, **kw):
            self.thread = threading.Thread(target=lambda:func(*args,**kw))
            self.thread.start() 
        return wrapper

    def rexit(self):
        #先停止测量数据
        self.loop=0
        if type(self.thread)==threading.Thread and threading.currentThread().ident!=self.thread.ident:
            self.thread.join(20)

        #再停止各仪器
        try:
            ins=['KEPCO电流源','6221']
            '''重置各仪器，然后断开与各仪器连接，最后退出程序'''
            if(not int(self.ins['6221'].query('SOUR:PDEL:NVPR?'))):
                ins.append('2182A')
            for name in ins:
                #连接各仪器,并初始化
                self.ins[name].clear()
                self.ins[name].write('*RST')
                self.ins[name].close()
            self.ins['F1208高斯计'].query('*RST\r')#初始化
            self.ins['F1208高斯计'].close()
    
        except:
            pass






