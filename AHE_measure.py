import sys,time,os
import pyvisa as visa
import threading
import numpy as np
import random
from tkinter import messagebox



class control(object):
    '''仪器控制
    属性：1.仪表名称以及所对应地址，2.ni-visa存放位置
    功能：1.设置输出电流，测量不同励磁电流下的电压值,把数据存放在列表中
    '''
    instruments={'2182A':'GPIB0::7::INSTR','2611A':'GPIB0::26::INSTR',
    'F1208高斯计':'ASRL3::INSTR','6211':'GPIB0::15::INSTR','KEPCO电流源':'GPIB0::6::INSTR'} #仪器及其所对应地址
    visa_dll = ''

    def __init__(self):
        self.rm=''
        self.data=[]  #用于存放读取来的数据
        self.instruments_list=''
        self.ins={}  #用于存放已经连接的仪器
        self.i_output=1e-3  #纵向输出电流，单位A
        self.n_average=2 #重复测量，取平均值的次数

        self.i_Magnet_min=-2.5 #0.08 #磁铁加的最小电流
        self.i_Magnet_max=2.5 #0.06 #磁铁加的最大电流
        self.n_Magnet=40 #磁铁从最小电流到最大电流之间点的数目  #细扫40个点


        self.width=50.0/1000 #纵向电流脉冲宽度

        self.i_count=0 #用于记录测量的数目
        self.ratio=9.1  #励磁电源电压与电流的比值，不能超过12

        self.loop=1 #测量开始后作为停止判断，只有loop设为0的时候才停止测量

        self.wait_time=0.4  #每次测量之间的间隔时间，单位s
        self.thread=''

    def initialization(self):
        '''
        1.参数初始化，包括励磁电流表
        2.仪器初始化，包括连接各仪器，设置停止位，重置各仪器等
        '''

        #生成励磁电流列表
        self.i_Magnet_list=np.linspace(self.i_Magnet_min,self.i_Magnet_max,self.n_Magnet+1)          
        self.i_Magnet_list=np.append(self.i_Magnet_list,self.i_Magnet_list[::-1])
        #print('励磁电流列表为：',self.i_Magnet_list)

        self.visa_dll = 'c:/windows/system32/visa64.dll'
        self.rm=visa.ResourceManager(self.visa_dll)        
        self.instruments_list=self.rm.list_resources()
        print('目前已连接的仪器有：',self.instruments_list)

        for name in ['KEPCO电流源','6211','2182A']:
            #连接各仪器,并初始化
            try:
                print(self.instruments[name])
                self.ins[name]=self.rm.open_resource(self.instruments[name])
                self.ins[name].write('*RST')
                print('成功连接'+name)
            except:
                print(name+'无法连接，程序退出')
                sys.exit()
        try:
            self.ins['F1208高斯计']=self.rm.open_resource(self.instruments['F1208高斯计'])
            self.ins['F1208高斯计'].read_termination = '\r' #F1208高斯计返回的结束符是\r
            self.ins['F1208高斯计'].query('*RST\r')#初始化
            self.ins['F1208高斯计'].query('RANGES 0') #自动定量程
        except:
            print(name+'无法连接，程序退出')
            sys.exit()            

        #self.ins['6211'].write('CURRent {}'.format(self.i_output)) #设置输出电流
        self.ins['6211'].write('OUTPUT ON')#开始输出电流

        self.ins['KEPCO电流源'].clear() #清除寄存器，不加这个，电流源可能不响应
        self.ins['KEPCO电流源'].write('OUTPUT ON')  #开始输出

    def rexit(self):
        #先停止测量数据
        self.loop=0
        if not self.thread:
            self.thread.join(20)

        #再停止各仪器
        try:
            '''重置各仪器，然后断开与各仪器连接，最后退出程序'''
            for name in ['KEPCO电流源','6211','2182A']:
                #连接各仪器,并初始化
                self.ins[name].clear()
                self.ins[name].write('*RST')
                self.ins[name].close()
            self.ins['F1208高斯计'].query('*RST\r')#初始化
            self.ins['F1208高斯计'].close()
        except:
            pass

    def AHE_meas_update(self):
        '''更新数据用，改变励磁电流，获取磁场和电压，计算得到电阻，并将数据保存'''
        try:
            print(self.i_count)
            i_Magnet=self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)] #确认励磁电流                

            if i_Magnet>6:
                #检测电流是否超过量程
                i_Magnet=6
                print('给定电流超过量程6A，已重设为6A')
                messagebox.showinfo("警告",'给定电流超过量程6A，已重设为6A')
            if i_Magnet*self.ratio>72:
                #检测电压是否超过量程
                self.ratio=72/i_Magnet
                print('给定电压超过量程72V，已重设为72V')
                messagebox.showinfo("警告",'给定电压超过量程72V，已重设为72V')        

            #设置励磁电流的输出电流以及电压
            self.ins['KEPCO电流源'].clear() #清除寄存器，不加这个，励磁电流源可能不响应
            self.ins['KEPCO电流源'].write('VOLT {:.4f};CURR {:.4f}'.format(i_Magnet*self.ratio,i_Magnet))
            print('励磁电流为'+'VOLT {:.4f};CURR {:.4f}'.format(i_Magnet*self.ratio,i_Magnet))
            time.sleep(self.wait_time*0.5)
            if(self.i_count==0):
                #第一个点等久点，让高斯计和材料都有反应时间
                time.sleep(2)

            #获取电压表所得电压,以及高斯计测得的磁场
            sum_R,sum_B=0,0 #用于计算平均值的中间变量
            for i in range(self.n_average):
                #多次测量，取平均值

                time.sleep(self.wait_time*0.5)
                self.ins['6211'].write('CURRent {}'.format(self.i_output)) #开始输出纵向电流
                time.sleep(self.width/2) #经过一段时间后开始测量电压
                meas_v=float(self.ins['2182A'].query(":READ?"))#获取电压
                time.sleep(self.width/2)
                self.ins['6211'].write('CURRent 0') #关闭电流源

                sum_R+=meas_v/(self.i_output)#计算得到电阻
                B=self.ins['F1208高斯计'].query('FIELD?\r')#读取磁场

                #判断磁场是否超量程，并将磁场数据由文本转化为字符串
                count=3
                while(B=='+1E' or B=='-1E'):
                    #超量程后重新读取
                    time.sleep(self.wait_time)
                    B=self.ins['F1208'].query('FIELD?\r')
                    count-=1
                    if(not count):
                        print('高斯计一直超量程，退出程序')
                        self.rexit()
                #字符串转数字
                sum_B+=float(B)
        except:
            #中间读取出了什么问题，不记录数据，返回重新下一次测量
            return -1
        self.i_count+=1 #计时器加1
        self.data.append([sum_B/self.n_average,sum_R/self.n_average])
    def update(self):
        '''循环更新数据，直至loop被设为0'''
        while(self.loop):
            if(len(self.data)>5000):
                #测量超过5000次，停止测量
                continue
            self.AHE_meas_update()
    def AHE_meas_start(self):
        '''主程序：测量数据，并实时更新'''

        #连接各仪器并初始化
        A.initialization()
        
        #更新数据
        self.thread = threading.Thread(target=self.update)
        self.thread.start()           

    def update_data_test(self):
        '''测试用，利用随机数来更新数据'''
        self.data.append([self.i_count,random.uniform(1,5)])
        self.i_count+=1  
    def update_test(self):
        '''循环更新数据，直至loop被设为0'''
        while(self.loop):
            if(len(self.data)>1000):
                continue
            self.update_data_test()
            time.sleep(0.5)
    def get_data(self):
        #返回数据
        return self.data        
    def start(self):
        #更新数据
        self.loop=1
        self.data=[]
        self.thread = threading.Thread(target=self.update_test)
        self.thread.start() 




