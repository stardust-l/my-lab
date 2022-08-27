# -*- coding: utf-8 -*-
from symtable import Symbol
import sys,time,os
import pyvisa as visa
import serial
import numpy as np
import random

class instrument(object):
    '''仪器控制
    仪表的一些基础控制，包括仪器的初始化，电压的测量，电流的设置，磁场的测量，磁场的设置
    '''
    instruments_GPIB={'2182A':'GPIB0::7::INSTR','2611A':'GPIB0::26::INSTR',
    '6221':'GPIB0::15::INSTR','KEPCO电流源':'GPIB0::10::INSTR','KEPCO电流源-6A':'GPIB0::6::INSTR','SR830_1':'GPIB0::8::INSTR','SR830_2':'GPIB0::9::INSTR'} #GPIB仪器及其所对应地址
    instruments_serial={'F1208高斯计':'ASRL3::INSTR','GCD0301M':'COM4'}#串口仪器及其所对应地址
    instrument={**instruments_GPIB,**instruments_serial}
    visa_dll = ''

    def __init__(self):
        self.ins={}#用于存放已经连接的仪器
        self.loop=0#用于判断测量结束没
        self.start_time=time.time()
        self.time=time.time() #用于记录时间
        self.data=[]  #用于存放读取来的数据
        self.i_count=0 #用于计数
        self.rate=1#2182A采样速率 #采样速率 0.1最快 1中等  5慢 
        self.sens_SR830_choosed=[20,17] #用于存放量程
        self.is_auto_range_1=1#是否自动调一次谐波的量程
        self.is_auto_range_2=1#是否自动调二次谐波的量程
        self.display_s=''
    def rsleep(self,t,T=0.2):
        #睡眠ts，当loop被置为0时，迅速返回
        while(t>0 and self.loop):
            time.sleep(T)
            t-=T
    def process_bar(self,percent, start_str='', end_str='', total_length=0):
        bar = ''.join(["\033[41m%s\033[0m"%' '] * int(percent * total_length)) + ''

        bar = '\r' + start_str + bar+' '*int(total_length-percent * total_length)+ ' {:0>4.1f}%|'.format(percent*100) + end_str
        print(bar, end='', flush=True)
    def check_quit(self,s='手动退出程序'):
        #检测到loop为0时，保存文件，抛出异常，以便迅速停止测量
        if(self.loop==0):
            assert False,s
    def link_ins(self,ins=''):
        '''探测有哪些仪器相连，并连接要求的仪器'''
        self.time=time.time()
        print('开始计时')
        name_linked=list(self.ins.keys())#已连接的仪器，防止再连一遍
        try:
            self.visa_dll = 'c:/windows/system32/visa64.dll'
            self.rm=visa.ResourceManager(self.visa_dll)     
            self.instruments_list=self.rm.list_resources()
            print('目前探测到的仪器地址有：',self.instruments_list)
        except:
            print('无法找到ni-visa，停止测量')
            assert 0  
        if(not ins):
            #没有指定连接的仪器，连接所有的仪器
            ins=[list (self.instrument.keys()) [list (self.instrument.values()).index (ins)] for ins in self.instruments_list]

        #连接串口仪器
        if('F1208高斯计' in ins and 'F1208高斯计' not in name_linked):
            try:
                print('开始尝试连接高斯计,其地址为:',self.instruments_serial['F1208高斯计'])
                ins_temp=self.rm.open_resource(self.instruments_serial['F1208高斯计'])#连接仪器
                self.ins['F1208高斯计']=ins_temp
                self.ins['F1208高斯计'].read_termination = '\r' #F1208高斯计返回的结束符是\r
                self.ins['F1208高斯计'].query('*RST\r')#初始化
                self.ins['F1208高斯计'].query('RANGES 0') #自动定量程
                print('成功连接高斯计')
            except Exception as e:
                print('高斯计无法连接，程序退出')
                assert 0
        if('GCD0301M'in ins and 'GCD0301M' not in name_linked):
            try:
                print('开始尝试连接GCD0301M,其地址为:',self.instruments_serial['GCD0301M'])
                ins_temp=serial.Serial(self.instruments_serial['GCD0301M'], baudrate=19200, stopbits=2,timeout=1)#连接仪器
                #ins_temp=self.rm.open_resource(self.instruments_serial['GCD0301M'])
                self.ins['GCD0301M']=ins_temp
                #self.ins['GCD0301M'].read_termination = '\r\n'
                print('成功连接GCD0301M')
            except Exception as e:
                print('GCD0301M电动转台无法连接，程序退出')
                print('detail:',e)
                assert 0
        #连接GPIB仪器
        ins_GPIB=[ins_one for ins_one in ins if ins_one not in name_linked+list(self.instruments_serial.keys())]#找出仪器中的GPIB接口的
        for name in ins_GPIB:
            try:
                print('开始尝试连接'+name+',其地址为:',self.instruments_GPIB[name])
                ins_temp=self.rm.open_resource(self.instruments_GPIB[name],timeout=3)#连接仪器
                self.ins[name]=ins_temp
                if('KEPCO电流源' in name):
                    if(name=='KEPCO电流源'):
                        print('检测到KEPCO电流源-14A,修改写入结束符')
                        self.ins[name].write_termination='\r'
                        
                        time.sleep(0.5)
                    self.ins[name].clear()
                    self.ins[name].write('*RST')
                    time.sleep(0.5)
                    self.ins[name].clear()
                    self.ins[name].write("OUTPUT ON")    
                else:
                    self.ins[name].write('*RST')
                self.ins[name].timeout=3000
                print('成功连接'+name)
            except:
                print(name+'无法连接，程序退出')
                self.ins.pop(name)
                assert 0
        #仪器初始设置
        if '2182A' in ins:
            #开始2182A的滤波
            self.ins['2182A'].write(':SENS:VOLT:LPAS ON')
            self.ins['2182A'].write(':SENS:VOLT:NPLC %g'%self.rate) #积分时间 0.1最快 1中等  5慢 
            print(self.rate)
            self.ins['2182A'].timeout=max(self.rate*800,2000)
        if '2611A' in ins:
            self.init_2611A()
    def link_ins_or(self,ins):
        #只要连接ins中的一个仪器便可
        try:
            visa_dll = 'c:/windows/system32/visa64.dll'
            rm=visa.ResourceManager(visa_dll)     
            instruments_list=rm.list_resources()
        except:
            print('无法找到ni-visa，停止测量')
            assert 0    
        for ins_one in ins:
            if self.instrument[ins_one] in instruments_list:
                self.link_ins([ins_one])
                return 0       
    def set_i_range(self,i_output):
        if i_output>10e-3:
            range=' i_output'
        elif i_output>1e-3:
            range=' 10e-3'
        else:
            range=' 1e-3'
        if('2611A' in self.ins.keys()):
            self.ins['2611A'].write('smua.source.rangei = {}'.format(range))
        if('6221' in self.ins.keys()):
            self.ins['6221'].write('SOUR:CURR:RANG{}'.format(range))
    def mea_V(self):
        '''读取电压'''
        self.check_quit()
        try:
            V=float(self.ins['2182A'].query(':READ?'))
        except:
            assert False,'2182A出现问题，可能是电压端断路'
        return V
        
    def pulse_mea_R(self,i_output=1e-3,i_pulse_width=10e-3,if_absorb=0):
        '''1.使用脉冲电流测量电阻，需将6221与2182A用288.2线连在一起,默认脉冲大小1mA，宽度10ms，2.也可用于往样品加脉冲电流，此模式的脉冲宽度为50微秒到10毫秒'''
        self.check_quit()
        if(if_absorb):
            self.ins['6221'].write('SOUR:SWE:ABOR')
            time.sleep(0.5)
        #print('ARM?',int(self.ins['6221'].query('PDELta:ARM?')))
        if(not int(self.ins['6221'].query('PDELta:ARM?'))):
            #查看6221是否准备完毕，没有的话设置脉冲后开始准备
            #电压上限(105v)，脉冲最高值(0.105)，最低值(-0.105)，宽度(50e-6到12e-3),2182A测量延时(16e-6到11.996e-3)
            #self.ins['6221'].write('*RST')
            print('开始设置脉冲:','加的脉冲大小为{:.2e},宽度为{:.2e}'.format(i_output,i_pulse_width))
            self.ins['6221'].write('*RST')
            time.sleep(1)#SOUR:PDEL:LME 0
            com='SOUR:PDEL:SWE OFF;CURR:COMP 60;SOUR:PDEL:HIGH {};SOUR:PDEL:LOW 0;SOUR:PDEL:LOW 0;SOUR:PDEL:WIDT {};SOUR:PDEL:SDEL {};'.format(i_output,i_pulse_width,i_pulse_width)

            #脉冲重复次数；脉冲间隔(5到999999)，例如5表示间隔5个交流电周期，交流电为50Hz时，一个完整测量周期为5/50=100ms；2182A量程自动
            com+='SOUR:PDEL:COUN 1;SOUR:PDEL:INT 5;SYST:COMM:SER:SEND ":SENS:VOLT:RANGE 0.1";'#:AUTO ON

            #6221量程为最合适的;准备开始
            com+='SOUR:PDEL:RANG BEST;SOUR:PDEL:ARM'
            #开始Pulse Delta模式的测量
            for c in com.split(';'):
                self.ins['6221'].write(c)
            while(not int(self.ins['6221'].query('PDELta:ARM?'))):
                time.sleep(0.5)
            #time.sleep(1)

        #读取6221数据,读取2182A的数据

        self.ins['6221'].write('INIT:IMM')
        time.sleep(1) #等待pulse delta测量结束
        
        V,data=list(map(float,self.ins['6221'].query('SENS:DATA?').split(',')))[:2]

        #打印数据
        print('测量电压为%.5e'%V,'未知数据%.5e'%data,'电阻为%.5e'%(V/i_output),sep=',')
        #self.ins['6221'].write('SOUR:SWE:ABOR')

        return V/i_output
    def base_mea_R(self,i_output=0.5e-3,if_rst=0,width=50e-3):
        '''测量电压，以得到电阻，只有测量时通电流,最后结果消去热电压'''
        self.check_quit()
        self.ins['6221'].write('OUTP ON')
        if(i_output>1e-3):
            self.ins['6221'].write('SOUR:CURR:RANG:AUTO ON')
        #开始输出纵向电流,并测电压
        self.set_i_DC(i_output=i_output,if_rst=if_rst) 
        time.sleep(width/2) #经过一段时间后开始测量电压
        meas_v=self.mea_V()#获取电压

        #转换电流方向再测一次，以消除热电压
        self.set_i_DC(i_output=-i_output)
        time.sleep(width/2)
        meas_v2=self.mea_V()

        #将电流源输出设为0
        self.set_i_DC(i_output=0)

        return (meas_v-meas_v2)/2/i_output#计算得到电阻，并返回 
    def init_2611A(self):
        '''2611A初始化'''
        rangei='1e-3'
        #设置输出直流；设置电流量程为1mA;电压限制为60V;
        com='smua.source.func = smua.OUTPUT_DCAMPS;smua.source.rangei = {};smua.source.limitv=60'.format(rangei)
        for c in com.split(';'):
            self.ins['2611A'].write(c)
    def base_mea_R_with_2611A(self,i_output=0.5e-3,if_rst=0,width=50e-3):
        '''2611A通电流，2182A测量电压，以得到电阻，只有测量时通电流,最后结果消去热电压'''
        self.check_quit()
        if(i_output>10e-3):
            #输出大于10mA，开启自动量程
            self.ins['2611A'].write('smua.source.autorangei=smua.AUTORANGE_ON')
        elif(i_output>1e-3):
            self.ins['2611A'].write('smua.source.rangei =10e-3')
        #开始输出纵向电流,并测电压
        if(if_rst):
            self.ins['2611A'].write('*RST')
            self.init_2611A()
        self.ins['2611A'].write('smua.source.leveli = {}'.format(i_output))
        self.ins['2611A'].write('smua.source.output = smua.OUTPUT_ON')#开始输出电压
        time.sleep(width/2) #经过一段时间后开始测量电压
        meas_v=self.mea_V()
        if True:
            #转换电流方向再测一次，以消除热电压
            self.ins['2611A'].write('smua.source.leveli = {}'.format(-i_output))
            time.sleep(width/2)
            meas_v2=self.mea_V()

            #将电流源输出设为0
            self.ins['2611A'].write('smua.source.leveli = 0')
            self.ins['2611A'].write('smua.source.output = smua.OUTPUT_OFF')#关闭输出

            return (meas_v-meas_v2)/2/i_output#计算得到电阻，并返回 
        #return meas_v/i_output
    def mea_R(self,i_output=1e-3,i_pulse_width=10e-3,if_rst=0):
        #测量电阻,根据连线情况挑选合适方式测量
        self.check_quit() 
        if('2611A' in self.ins.keys()):
            R=self.base_mea_R_with_2611A(i_output=i_output,if_rst=if_rst)
        elif('6221' in self.ins.keys()):
            if(not int(self.ins['6221'].query('SOUR:PDEL:NVPR?'))):
                R=self.base_mea_R(i_output=i_output,if_rst=if_rst)
            else:
                R=self.pulse_mea_R(i_output=i_output,i_pulse_width=10e-3,if_absorb=if_rst)
        else:
            assert 0,'未连接6221或者2611A'
        return R     
    def set_i_DC_6221(self,i_output=0.2e-3,if_rst=0):
        '''设置直流电流'''
        if(if_rst):
            self.ins['6221'].write('*RST')
        self.ins['6221'].write('SOUR:CURR:COMP 45')#40V电压限制
        self.ins['6221'].write('OUTP ON')
        self.ins['6221'].write('CURRent {}'.format(i_output))
    def set_i_DC_2611A(self,i_output=0.2e-3,if_rst=0):
        '''设置直流电流'''
        if(if_rst):
            self.ins['2611A'].write('*RST')
            self.init_2611A()
        self.set_i_range(i_output=i_output)
        self.ins['2611A'].write('smua.source.leveli = {}'.format(i_output))
        self.ins['2611A'].write('smua.source.output = smua.OUTPUT_ON')#开始输出电流
    def set_i_DC(self,i_output=0.2e-3,if_rst=0):
        if('6221' in self.ins.keys()):
            self.set_i_DC_6221(i_output,if_rst)
        elif('2611A' in self.ins.keys()):
            self.set_i_DC_2611A(i_output,if_rst)
    def set_i_SIN(self,freq=133,i_AMPL=1e-3,if_rst=1,if_init=1,if_absorb=0):
        '''设置正弦输出的脉冲，默认不停止'''
        self.check_quit()
        if if_rst:
            self.ins['6221'].write('*RST')
        if if_init:
            #选择正弦波；设置频率；设置振幅；输出触发信号低电平不接地
            com='SOUR:WAVE:FUNC SIN;SOUR:WAVE:FREQ {};SOUR:WAVE:AMPL {};OUTPut:LTEarth OFF;'.format(freq,i_AMPL)
            #开启相位标记；在180度时输出一个触发信号；触发信号通过3通道输出；最佳量程;准备开始
            com+='SOUR:WAVE:PMAR:STAT ON;SOUR:CURR:COMP 40;SOUR:WAVE:PMAR 180;SOUR:WAVE:PMAR:OLIN 3;SOUR:WAVE:RANG BEST;SOUR:WAVE:ARM'
            for c in com.split(';'):
                self.ins['6221'].write(c)
            '''while(True):
                self.check_quit()
                self.rsleep(1)
                if int(self.ins['6221'].query('SOUR:WAVE:ARM?')):
                    break'''
            self.ins['6221'].write('SOUR:WAVE:INIT')
        if if_absorb:
            self.ins['6221'].write('SOUR:WAVE:ABOR')        
    def set_i_pulse_SWE(self,i_output=1e-3,i_pulse_width=1e-3,if_absorb=1,if_init=1,if_rst=0):
        '''用以输出脉冲，两种模式'''
        V_limited=60
        self.check_quit()
        if(i_pulse_width>=1e-3):
            if(if_rst):
                self.ins['6221'].write('*RST')
                time.sleep(0.5)
            print('开始设置脉冲:','加的脉冲大小为{:.2f}mA,宽度为{:.2f}ms'.format(1000*i_output,1000*i_pulse_width))
            command=''#用以放置传给6221的命令
            command+='SOUR:SWE:SPAC LIST;SOUR:SWE:RANG AUTO;' #选择自定义模式；量程自动选择 2e-4
            command+='SOUR:LIST:CURR {},0;SOUR:LIST:DEL {},10e-3;SOUR:LIST:COMP {},20;'.format(i_output,i_pulse_width,V_limited)#设定脉冲电流大小（-0.105到0.105A);脉冲宽度（0.001到999s）;电压上限（0.1-105V）
            command+='SOUR:SWE:COUN 1;SOUR:SWE:CAB ON;'#循环次数一次;电压超限制后不停止
            command+='SOUR:SWE:ARM'#准备输出；开始输出脉冲
            for com in command.split(';'):
                self.ins['6221'].write(com)
            time.sleep(0.1)
            self.ins['6221'].write('INIT')
            if(if_absorb):
                self.ins['6221'].write('SOUR:SWE:ABOR')
        elif(i_pulse_width<1e-3):
            self.loop=0
            print('脉冲小于1ms的函数还未完成')
        if(abs(i_output)<1e-9):
            self.ins['6221'].write('SOUR:CURR:RANG 1e-3')       
    def set_i_pulse_SQU(self,i_output=1e-3,i_pulse_width=1e-3,if_absorb=1,if_init=1,if_rst=1):
        '''以方波形式输出脉冲，还有待测试'''
        self.check_quit()
        commod=''
        if(i_pulse_width<5e-6 or i_pulse_width>1):
            input('请确保输入的脉冲宽度在5微秒到1s之间')
            assert 0,'脉冲宽度不符合格式'
        
        if(if_init):
            #是否重新设置脉冲信息
            if(i_output>1e-8):
                #脉冲为正的时候选用正的周期，即占空比调到100 
                DCYC=100
            elif(i_output<-1e-8):
                #脉冲为负的时候选用负的周期，即占空比调到0
                DCYC=0
            elif(abs(i_output)<1e-8):
                #脉冲大小为0时，直接返回
                print('脉冲大小为{:g}mA,宽度为{:g}ms'.format(i_output*1000,i_pulse_width*1000))
                return 0
            if(if_rst):
                self.ins['6221'].write('*RST')
                self.ins['6221'].write('SOUR:CURR:COMP 60')#60V电压限制
            freq=min(pow(10,-int(np.log10(i_pulse_width))),1e5) #根据所需要脉冲宽度，合理选择频率和脉冲持续时间
            DUR_TIME=i_pulse_width
            commod=''
            print('脉冲大小为{:g}mA,宽度为{:g}ms'.format(i_output*1000,i_pulse_width*1000))
            print('选择的方波频率为{:g}Hz,生成时间为{:g}s'.format(freq,DUR_TIME))
            #选择方波;占空比，单位%;脉冲大小;波形持续时间，最短1微秒;最佳量程
            commod+='SOUR:WAVE:FUNC SQU;SOUR:WAVE:FREQ {};SOUR:WAVE:AMPL {};SOUR:WAVE:DCYC {};SOUR:WAVE:DUR:TIME {};SOUR:WAVE:RANG BEST;'.format(freq,abs(i_output),DCYC,DUR_TIME)
            #准备开始
            commod+='SOUR:WAVE:ARM'
            for c in commod.split(';'):
                self.ins['6221'].write(c)
            time.sleep(0.1)
            self.ins['6221'].write('SOUR:WAVE:INIT')#开始输出脉冲
            time.sleep(0.2)
        if(if_absorb):
            #是否取消准备
            self.ins['6221'].write('SOUR:WAVE:ABOR')
            time.sleep(0.2)
    def set_i_pulse_with_2611A(self,i_output=1e-3,i_pulse_width=1e-3):
        #加脉冲
        if(i_pulse_width<1e-3):
            print('2611A此模式下脉冲宽度需要大于1ms')
            self.rsleep(10)
        V_COM=60#限制电压
        self.ins['2611A'].write('smua.measure.nplc=0.005')
        self.ins['2611A'].write('smua.source.limitv = {}'.format(V_COM))
        self.ins['2611A'].write('PulseIMeasureV(smua, 0, {},{}, 20E-3, 1)'.format(i_output,i_pulse_width))#sma通道a;偏压;脉冲大小;脉冲宽度;间隔宽度
        #print(self.ins['2611A'].query('compliance = smua.source.compliance;print(compliance)'))
        time.sleep(0.5)
        print('加的脉冲大小为{}mA,宽度为{}ms'.format(i_output*1000,i_pulse_width*1000))
        V_L=float(self.ins['2611A'].query('printbuffer(1, 1, smua.nvbuffer1.readings)'))
        print('2611A测得纵向电压为',V_L,'V')
        if(abs(V_L)>V_COM*0.98):
            print('电压已达到上限！！！请注意！！！')
            self.rsleep(5)
    def set_i_pulse_with_2611B_trigger_mode(self,i_output=1e-3,i_pulse_width=1e-3):
        if(i_pulse_width<0.5e-6):
            print('2611A此模式下脉冲宽度需要大于0.5us,到1000s')
            self.rsleep(10)
        #加脉冲,triggle_mode 0.9us-
        V_COM=60#限制电压
        self.ins['2611A'].write('smua.trigger.source.listi({%g})'%i_output)
        self.ins['2611A'].write(r'smua.trigger.source.action = smua.ENABLE')
        self.ins['2611A'].write(r'smua.trigger.measure.action = smua.DISABLE')
        self.ins['2611A'].write('smua.source.limitv = {}'.format(V_COM))
        self.set_i_range(i_output)#设置量程
        self.ins['2611A'].write('trigger.timer[1].delay = {:g}'.format(i_pulse_width))
        self.ins['2611A'].write('trigger.timer[1].count = 1')
        self.ins['2611A'].write('trigger.timer[1].passthrough = false')
        self.ins['2611A'].write('trigger.timer[1].stimulus = smua.trigger.ARMED_EVENT_ID')
        self.ins['2611A'].write('smua.trigger.source.stimulus = 0')#开始后不延迟，立马开始
        self.ins['2611A'].write('smua.trigger.endpulse.action = smua.SOURCE_IDLE')
        self.ins['2611A'].write('smua.trigger.endpulse.stimulus = trigger.timer[1].EVENT_ID')
        self.ins['2611A'].write('smua.trigger.count = 1')
        self.ins['2611A'].write('smua.trigger.arm.count = 1')
        self.ins['2611A'].write('smua.source.output = smua.OUTPUT_ON')
        self.ins['2611A'].write('smua.trigger.initiate()')#开始加脉冲
        self.rsleep(0.4)
        print('加的脉冲大小为{}mA,宽度为{}ms'.format(i_output*1000,i_pulse_width*1000))
        
    def set_i_pulse(self,i_output=1e-3,i_pulse_width=1e-3,if_absorb=1,if_init=1,if_rst=1):
        if('2611A' in self.ins.keys()):
            self.set_i_pulse_with_2611A(i_output,i_pulse_width)
        elif('6221' in self.ins.keys()):
            return self.set_i_pulse_SQU(i_output,i_pulse_width,if_absorb,if_init,if_rst)
    '''二、谐波测量部分'''
    def init_HARM_com(self,HARM=1,n_SR830=0,PHAS=0):
        #锁相参数的初始化设置
        self.sens_SR830_1_choosed=20
        #利用外部电流源；用0正弦零点，1下降沿，2上升沿；谐波次数;输入选择A-B;接地选择0浮地,1接地;滤波方式，全选;
        com='FMOD 0;RSLP 2;HARM {};ISRC 1;IGND 0;ILIN 0;'.format(HARM)
        #RMOD 动态存储（即容忍最大量程几倍的噪声），0high reserve,1正常,2低噪声;低通滤波阶数;开启同步滤波；面板显示物理量，1通道，0为X,1为R,2为x noise，2通道，0为Y，1为theta,2为Y noise；开始测量
        com+='OFSL 2;SYNC 0;DDEF 1,0,0;DDEF 2,0,0;'
        #设置量程；开始测量
        
        if(n_SR830==0):
            #选择几号SR830
            #9，时间常数300ms
            com+='RMOD 1;OFLT 9;SENS {};PHAS 0;START'.format(self.sens_SR830_choosed[0])
            ins=self.ins['SR830_1']
        else:
            #时间常数10：1s；9：300ms
            com+='RMOD 1;OFLT 9;SENS {};PHAS 90;START'.format(self.sens_SR830_choosed[1])
            ins=self.ins['SR830_2']
        ins.write(com)

    def init_HARM_inter(self,HARM=1,V=2):
        #锁相初始化
        #设定频率;用正弦波零点；谐波次数;设定电压;输入选择A-B;接地选择浮地;滤波方式，全选3;
        com='FREQ 133;RSLP 0;HARM {};SLVL {};ISRC 1;IGND 0;ILIN 0'.format(HARM,V)
        #最低噪声;时间常数8，100ms;低通滤波阶数;开启同步滤波；开始测量
        com+='RMOD 2;OFLT 9;OFSL 3;SYNC 1;START'
        self.ins['SR830_1'].write(com)
    def mea_V_HARM(self,n_SR830=0,n_average=5,Min_of_range=0.3):
        '''利用锁相来测量电压'''
        #确认量程
        sens_list=[2e-9,5e-9]
        for i in range(8):
            sens_list.extend([1*pow(10,-8+i),2*pow(10,-8+i),5*pow(10,-8+i)])
        sens_list.extend([1])
        if(n_SR830==0):
            i_sens=0
            ins=self.ins['SR830_1']
        elif n_SR830==1:
            i_sens=1
            ins=self.ins['SR830_2']
        while(True):
            #超量程了自动调整量程，初始设为1微伏
            self.check_quit()
            params=ins.query('SNAP?3,4').split(',')#读取R,theta 1是x，2是y，3是R，4是theta
            R=float(params[0])
            theta=float(params[1])
            #print('R:',R,'theta:',theta)
            if(abs(R)<sens_list[self.sens_SR830_choosed[i_sens]]*Min_of_range):
                #当小于量程的30%时且不是最小量程，减小量程
                if(self.sens_SR830_choosed[i_sens]==0):
                    #当是最小量程时，直接返回数值
                    print('已达到最小量程2nV')
                    return R*(2*int(theta>=0 and theta<=180)-1)
                else:
                    #否则减小量程
                    self.sens_SR830_choosed[i_sens]-=1
                    ins.write('SENS {}'.format(self.sens_SR830_choosed[i_sens]))
            elif(abs(R)>sens_list[self.sens_SR830_choosed[i_sens]]*0.9):
                #当测量值大于量程的95%时且不是最大量程，增大量程
                if(self.sens_SR830_choosed[i_sens]==26):
                    #当是最大量程时，直接返回数值
                    print('已达到最大量程1V')
                    return R*(2*int(theta>=0 and theta<=180)-1)
                else:
                    #否则增大量程
                    self.sens_SR830_choosed[i_sens]+=1
                    ins.write('SENS {}'.format(self.sens_SR830_choosed[i_sens]))
            else:
                #在量程的30%到95%之间，则可以直接返回数值
                sum_V=0
                for i in range(n_average):
                    params=ins.query('SNAP?3,4').split(',')#读取R,theta 1是x，2是y，3是R，4是theta
                    R=float(params[0])
                    theta=float(params[1])
                    sum_V+=R*(2*int(theta>=0 and theta<=180)-1)
                return sum_V/n_average
            time.sleep(1)
            if(n_SR830==1):
                self.rsleep(4)
    def init_HARM_com_togather(self):
        self.init_HARM_com(HARM=1,n_SR830=0)
        self.init_HARM_com(HARM=2,n_SR830=1)
    def mea_V_HARM_togather(self,n_average=5,freq=133):
        '''几乎同时测量一次和二次谐波的读数'''
        #先调整量程
        if(self.is_auto_range_1):
            self.mea_V_HARM(n_SR830=0,n_average=1)
        if(self.is_auto_range_2):
            self.mea_V_HARM(n_SR830=1,n_average=1,Min_of_range=0.2)
        #测量数据
        sum1,sum2=[],[]
        for i in range(n_average):
            #多次测量，返回中位数
            params1=self.ins['SR830_1'].query('SNAP?1,2').split(',')#读取R,theta 1是x，2是y，3是R，4是theta
            params2=self.ins['SR830_2'].query('SNAP?1,2').split(',')#读取R,theta 1是x，2是y，3是R，4是theta
            X1,Y1=float(params1[0]),float(params1[1])
            X2,Y2=float(params2[0]),float(params2[1])

            sum1.append([X1,Y1])
            sum2.append([X2,Y2])
            """R1,R2=float(params1[0]),float(params2[0])
            theta1,theta2=float(params1[1]),float(params2[1])
            sum_V1+=R1*(2*int(theta1>=0 and theta1<=180)-1)
            sum_V2+=R2*(2*int(theta2>=0 and theta2<=180)-1) """
        return np.append(np.median(sum1,axis=0), np.median(sum2,axis=0))       

    '''三、设置磁场相关部分'''
    def mea_B(self):
        while(True):
            try:
                return float(self.ins['F1208高斯计'].query('FIELD?\r'))
            except:
                pass
    def mea_B_exact(self,error=1,wait_time=0.3):
        '''等待磁场稳定后测量磁场'''
        self.check_quit()
        B1=100000
        if(error<0.05):
            #如果误差过小，增加两个点之间测量的时间间隔，最长2秒
            wait_time*=min(0.1/error,7)
        count=3
        while(True):
            #两次测量差别大于误差，就一直测量
            try:
                self.check_quit()
                time.sleep(wait_time)
                B=self.ins['F1208高斯计'].query('FIELD?\r')#读取磁场
                if(error<0):
                    error=-error
                while(abs(float(B))<1e-5 and count!=1):
                    #有时候超量程会返回0
                    time.sleep(0.5)
                    B=self.ins['F1208高斯计'].query('FIELD?\r')#读取磁场
                    #print('磁场大小:',B)
                    count-=1
                count=3
                while(B=='+1E' or B=='-1E'):
                    #超量程后重新读取
                    time.sleep(wait_time)
                    B=self.ins['F1208高斯计'].query('FIELD?\r')
                    count-=1
                    if(not count):
                        print('高斯计一直超量程，退出程序')
                        self.loop=0
                        assert 0,'高斯计一直超量程'
                if(abs(B1-float(B))<error or error>=99):
                    #短时间变化小于一定值才停止测量
                    return float(B)
                B1=float(B)
            except Exception as e:
                self.check_quit()
                print('磁场测量出现问题，重新测量')
                print('原因：',e)
                count-=1
                if(not count):
                    self.loop=0
                    assert 0,'磁场测量出问题'
    def set_i_Magnet(self,i_Magnet,radio=9.3,i_max=5.5):
        '''给励磁电流源加上要求的电流'''
        self.check_quit()
        if abs(i_Magnet)>i_max:
            #检测电流是否超过量程
            i_Magnet=i_max*i_Magnet/abs(i_Magnet)
            print('给定电流超过量程{:.1f}A，已重设为{:.1f}A'.format(i_max,i_max))
            print("警告",'给定电流超过量程{:.1f}A，已重设为{:.1f}A'.format(i_max,i_max))      

        #设置励磁电流源的输出
        time.sleep(0.3)
        self.ins['KEPCO电流源'].clear() #清除寄存器，不加这个，励磁电流源可能不响应
        self.ins['KEPCO电流源'].write('CURR {:.5f};VOLT {:.5f}'.format(i_Magnet,i_Magnet*radio))
        #print('励磁电流为'+'CURR {:.4f}'.format(i_Magnet))
    def set_V_Magnet(self,V_Magnet,radio=9,Vmax=70):
        '''给励磁电流源加上要求的电压'''
        self.check_quit()
        if abs(V_Magnet)>Vmax:
            #检测电流是否超过量程
            V_Magnet=Vmax*V_Magnet/abs(V_Magnet)
            print("警告",'给定电压超过量程{:g}V，已重设为{:g}V'.format(Vmax,Vmax))      

        #设置励磁电流源的输出
        self.ins['KEPCO电流源'].clear() #清除寄存器，不加这个，励磁电流源可能不响应
        self.ins['KEPCO电流源'].write('VOLT {:.5f};CURR {:.5f}'.format(V_Magnet,V_Magnet/radio))
          
    def set_B_Magnet_old(self,B_target,error=1.3,if_exact=1):
        #迭代设置到设定磁场
        delta_B=B_target-self.mea_B_exact(error=20)#得到现在的磁场和目标磁场的偏差#现在磁场与目标磁场的差值

        self.ins['KEPCO电流源'].clear()
        V=float(self.ins['KEPCO电流源'].query('VOLT?'))
        kp=8.0/2000#比例项系数
        print('目标磁场为:',B_target,'Oe',sep='')

        if(abs(B_target)<201 and if_exact):
            if(abs(B_target)<=2):
                error=0.01
            else:
                error=np.log10(abs(B_target))*0.001 
        count=0
        while(abs(delta_B)>error):
            #sum_delta_B+=+delta_B_temp
            #根据误差设定比例系数
            if(abs(delta_B)<100):
                kp=6.0/2000
            if(abs(delta_B)<2 and abs(delta_B)>1):
                kp=5.0/2000
                time.sleep(1)
                #kp=kp*np.power(0.7,count//3)
            if(abs(delta_B)<1):
                kp=2.0/2000
                time.sleep(1) 
            if(abs(delta_B)>500):
                kp=1/2000
                count=0
                time.sleep(1)
            if(abs(delta_B)<500 and abs(delta_B)>110):
                kp=2/2000
                count=0
                time.sleep(1)            

            
            if(abs(B_target)>200):
                skip=1
                if(count>skip):
                    #太久没调好，误差区间调大一些,前skip个点不予记录
                    if(count>40):
                        count=skip+4
                    kp=kp*np.power(0.9,(count-skip)//4)
                    error+=0.03*((count-skip)//9)
                count+=1

            B_min=4e-4*abs(delta_B)/delta_B
            deltaV=sorted([kp*(delta_B),B_min],key=abs)[-1]#用比例控制，得到要加的励磁电流 +sum_delta_B/10
            print('变化电压为：%.5fV'%deltaV,'距离目标磁场距离为：%.3fOe,'%delta_B,'容忍误差为%gOe'%error,sep='')
            print('现励磁电压为%.5f'%V)
            self.ins['KEPCO电流源'].clear() 
            time.sleep(1)
            #V=float(self.ins['KEPCO电流源'].query('MEAS:VOLT?')) 
            V+=deltaV
            
            if(abs(V)>72 and count>=6):
                print('目标磁场过大,仪器不能达到要求')
                return [72,6]
            self.set_V_Magnet(V)
            #time.sleep(min(1/abs(delta_B),0.2))
            delta_B=B_target-self.mea_B_exact(error=max(abs(delta_B)*0.1,0.04))
                
        print('设置完成，实际磁场为%.2f'%(-delta_B+B_target),'目标磁场为:%.1f'%B_target)
        self.ins['KEPCO电流源'].clear()
        V=float(self.ins['KEPCO电流源'].query('VOLT?'))
        time.sleep(1)
        self.ins['KEPCO电流源'].clear()
        I=float(self.ins['KEPCO电流源'].query('CURR?'))
        print('励磁电压为：{:.5f},励磁电流为:{:.5f}'.format(V,I))
        return [V,I]
    def set_B_Magnet(self,B_target,error=1.3,if_exact=1,n_count=-10,ratio_space=1):
        #使用PID控制，实现磁场的控制
        delta_B=B_target-self.mea_B_exact(error=20)#得到现在的磁场和目标磁场的偏差#现在磁场与目标磁场的差值

        self.ins['KEPCO电流源'].clear()
        V=float(self.ins['KEPCO电流源'].query('VOLT?'))#得到当前的磁场
        print('目标磁场为:',B_target,'Oe',sep='')
        if(abs(delta_B)>3000):
            Kp=3/2000#比例项系数
            Kd=Kp*0.21#微分项系数
        elif(abs(delta_B)>500):
            Kp=4/2000
            Kd=Kp*0.15#微分项系数
        else:
            Kp=6.0/2000
            Kd=Kp*0.03#微分项系数            
        Ki=Kp*0.5#积分项系数
        
        I_item=0#积分项
        I_item_max=1000#积分项最大值
        delta_B_last=delta_B#上一次的差值，用于微分项
        count=0#计数器

        if(if_exact and abs(B_target)<201):
            #目标磁场小于200Gs，设置精度高些
            if(abs(B_target)<=50):
                error=0.01
            else:
                error=0.1#np.log10(abs(B_target))*0.01 


        while(True):
            count+1
            n_count+=1#长时间调不到的话，增加误差容忍度
            if(n_count>=3):
                error+=0.05
                n_count=0

            P_item=Kp*delta_B#比例项
            
            if(abs(delta_B)<5):
                #误差小于5Gs，开始计入积分项
                I_item+=delta_B#积分项
            if(abs(I_item)>I_item_max):
                #积分项超过最大值，设置为最大值
                I_item=I_item/abs(I_item)*I_item_max

            D_item=delta_B-delta_B_last#计算微分项
            delta_B_last=delta_B
            deltaV=(P_item+Ki*I_item+Kd*D_item)*ratio_space#计算要变化的电压
            print('变化电压为：%.5fV'%deltaV,'距离目标磁场距离为：%.3fOe,'%delta_B,'容忍误差为%gOe'%error,sep='')
            print('现励磁电压为%.5f'%V)
            self.ins['KEPCO电流源'].clear() 
            time.sleep(1)
            V+=deltaV
            
            if(abs(V)>72 and count):
                print('目标磁场过大,仪器不能达到要求')
                return [72,6]
            self.set_V_Magnet(V)
            #time.sleep(min(1/abs(delta_B),0.2))
            delta_B=B_target-self.mea_B_exact(error=max(abs(delta_B)*0.1,0.04))
            if(abs(delta_B)<abs(error)):
                self.rsleep(1.5)
                delta_B=B_target-self.mea_B_exact(error=max(abs(delta_B)*0.1,0.04))
                if(abs(delta_B)<abs(error)):
                    break
        print('设置完成，实际磁场为%.2f'%(-delta_B+B_target),'目标磁场为:%.1f'%B_target)
        self.ins['KEPCO电流源'].clear()
        V=float(self.ins['KEPCO电流源'].query('VOLT?'))
        time.sleep(1)
        self.ins['KEPCO电流源'].clear()
        I=float(self.ins['KEPCO电流源'].query('CURR?'))
        print('励磁电压为：{:.5f},励磁电流为:{:.5f}'.format(V,I))
        return [V,I]    
    '''四、电机部分'''
    def rotation(self,angle=5,speed=150,subdivision=2,if_exit=0):
        #toward #1：示数减少，0：示数增加
        #angle #旋转角度
        #speed 旋转速度
        #subdivision #细分数
        #确定方向
        if(angle==0):
            print('旋转0°')
            return 0
        elif(angle>0):
            toward=0
        else:
            toward=1
        distance='{:0>8X}'.format(int(abs(angle)*200*subdivision//2))
        speed='{:0>2X}'.format(150)#速度不要超过200
        command='@1D0{}S{}P{}G\r\n'.format(toward,speed,distance).encode('utf8')
        self.ins['GCD0301M'].write(command)

        while(True):
            #等待旋转命令执行完
            self.ins['GCD0301M'].write('@1R0001\r\n'.encode('utf8'))
            time.sleep(0.3)
            if(self.ins['GCD0301M'].read(10)==b'#1R01\r\n'):
                print('旋转{:g}°执行完毕,实际转动{:g}°'.format(angle,int(angle*200*subdivision//2)/200/subdivision*2))
                break
        if if_exit:
            self.check_quit()
        return int(angle*200*subdivision//2)/200/subdivision*2
    '''其他'''
    def init_common(self):
        #通用的初始化设置
        self.loop=1
        self.data=[]
        self.i_count=0
    def rexit(self,s_quit='测量结束'):
        '''退出程序，断开与所有仪器的连接'''
        self.loop=0
        name=[n for n in self.ins.keys()]
        try:
            for common_ins in self.instruments_GPIB.keys():
                #GPIB仪器结束过程一样
                if common_ins in name:
                    self.ins[common_ins].clear()
                    self.ins[common_ins].write('*RST')
                    if('KEPCO电流源' in common_ins):
                        time.sleep(0.5)
                        self.ins[common_ins].clear()
                        self.ins[common_ins].write('output off')
                        time.sleep(0.5)
                        self.ins[common_ins].clear()
                        self.ins[common_ins].write('VOLT 0')
                        time.sleep(0.5)
                        self.ins[common_ins].clear()
                        self.ins[common_ins].write('CURR 0')
                    self.ins[common_ins].close()  
                    print('成功关闭',common_ins)
                    self.ins.pop(common_ins)
            if('F1208高斯计' in name):
                self.ins['F1208高斯计'].query('*RST\r')#初始化
                self.ins['F1208高斯计'].close()   
                print('成功关闭高斯计')  
                self.ins.pop('F1208高斯计')    
            if('GCD0301M' in name):
                self.ins['GCD0301M'].close()   
                print('成功关闭GCD0301M')  
                self.ins.pop('GCD0301M')           
        except Exception as e:
            print('仪器断开过程中遇到问题')
            print('细节：',e)
        t=time.time()-self.time
        print('{},耗时{}分{:.3f}秒'.format(s_quit,t//60,t%60))
    '''五、热部分'''
    def heat(self,i_heat,t_wait=10*60,if_set_range=True):
        #以i_heat大小的电流加热,并等待一段时间
        import colorama
        colorama.init(autoreset=True)
        self.temp_flag=1#若为0，加热结束
        if(if_set_range):
            self.set_i_range(i_output=i_heat)

        self.set_i_DC(i_output=i_heat)#开始加热

        t0=time.time()
        t=0
        while(t<t_wait):
            #一直等稳定了再进行下一步
            self.check_quit()
            V_sample=self.mea_V()
            if(self.temp_flag==0):
                print('手动停止加热')
                break
            
            t=time.time()-t0
            if '6221' in self.ins.keys():
                self.data.append([t,V_sample])
            elif '2611A' in self.ins.keys():
                V_heat=float(self.ins['2611A'].query('print(smua.measure.v())'))
                self.data.append([t,V_sample,V_heat])                
            end_str ='100%   已加热{:.0f}秒|总共{:.0f}秒'.format(t,t_wait)
            self.process_bar(t/t_wait, start_str='', end_str=end_str, total_length=30)
        print('加热完成，开始下一步测量')
    def close_all(self):
        #强制关闭所有仪器
        name=[n for n in self.ins.keys()]
        if(len(name)>0):
            print(name,'仍未关闭，强制关闭中')
            for ins_name in name:
                self.ins[ins_name].close()
            self.ins={}
if __name__=='__main__':
    #测试仪器通讯命令
    try:
        pass
    except Exception as e:
        print('e:',e)
    test=instrument()
    test.loop=1
    test.link_ins(ins=['2182A','KEPCO电流源'])
    test.set_i_Magnet(0)
    input('stop')
    test.rexit()


