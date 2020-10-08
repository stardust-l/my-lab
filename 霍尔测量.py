import sys,time,visa,os
import threading
import numpy as np
import random
from tkinter import messagebox
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout

class control(object):
    '''仪器控制
    属性：1.仪表名称以及所对应地址，2.ni-visa存放位置
    功能：1.设置输出电流，测量不同励磁电流下的电压值
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

        #生成励磁电流列表
        self.i_Magnet_list=np.linspace(self.i_Magnet_min,self.i_Magnet_max,self.n_Magnet+1)  
        
        self.i_Magnet_list=np.append(self.i_Magnet_list,self.i_Magnet_list[1:-1][::-1])
        print(self.i_Magnet_list)
        #用于测量有效场
        self.i_output_list=[self.i_output]*len(self.i_Magnet_list)+[self.i_output]*len(self.i_Magnet_list)
        self.i_temp=self.i_output_list[0]

        self.i_count=0 #用于记录测量的数目
        self.ratio=9.1  #励磁电源电压与电流的比值，不能超过12

        self.loop=1
        
        self.fold='data'
        if not os.path.exists(self.fold):
            os.makedirs(self.fold)
        self.name=''
        #self.path=self.fold+'/'+self.name+'-n-number_{}-i_measure_{}.txt'.format(self.n_Magnet,self.i_output)
        self.path=''

        self.t1='' #用于存放多线程

        self.wait_time=0.4  #每次测量之间的间隔时间，单位s
    def rexit(self):
        '''重置各仪器，然后断开与各仪器连接，最后退出程序'''
        for name in ['KEPCO电流源','6211','2182A']:
            #连接各仪器,并初始化
            self.ins[name].clear()
            self.ins[name].write('*RST')
            self.ins[name].close()
        self.ins['F1208高斯计'].query('*RST\r')#初始化
        self.ins['F1208高斯计'].close()

    def initialization(self):
        '''仪器初始化，包括连接各仪器，设置停止位，重置各仪器等'''

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

        self.ins['6211'].write('CURRent {}'.format(self.i_output)) #设置输出电流
        self.ins['6211'].write('OUTPUT ON')#开始输出电流

        self.ins['KEPCO电流源'].clear() #清除寄存器，不加这个，电流源可能不响应
        self.ins['KEPCO电流源'].write('OUTPUT ON')  #开始输出
        self.ins['KEPCO电流源'].clear() #清除寄存器，不加这个，电流源可能不响应
        self.ins['KEPCO电流源'].write('VOLT {:.4f};CURR {:.4f}'.format(self.i_Magnet_list[0]*self.ratio,self.i_Magnet_list[0]))
        time.sleep(self.wait_time*2)
    def AHE_meas_update(self):
        '''更新数据用，改变励磁电流，获取磁场和电压，计算得到电阻，并将数据保存'''
        try:
            print(self.i_count)
            i_output=self.i_output_list[self.i_count%len(self.i_output_list)] #确认输出电流
            i_Magnet=self.i_Magnet_list[self.i_count%len(self.i_Magnet_list)] #确认励磁电流

            if(self.i_count==0):
                self.i_temp=i_output

            elif(i_output!=self.i_temp):
                self.i_temp=i_output
                self.ins['6211'].write('CURRent {}'.format(i_output)) #设置输出电流
                

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

            #获取电压表所得电压,以及高斯计测得的磁场
            sum_R,sum_B=0,0 #用于平均的中间变量
            for i in range(self.n_average):
                #多次测量，取平均值
                time.sleep(self.wait_time*0.5)
                meas_v=float(self.ins['2182A'].query(":READ?"))#获取电压
                sum_R+=meas_v/(i_output)#计算得到电阻
                B=self.ins['F1208高斯计'].query('FIELD?\r')

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
            return -1
        self.i_count+=1 #计时器加1
        self.data.append([sum_B/self.n_average,sum_R/self.n_average])
    def update(self):
        '''循环更新数据，直至loop被设为0,测试用'''
        while(self.loop):

            if not self.t1:
                #当线程为空时，直接开始一个新的测量线程
                self.t1 = threading.Timer(self.wait_time,self.AHE_meas_update)  #定时wait_time*5秒测量一组数据
            else:
                #仅当上一个线程结束后才进行下一个
                self.t1.join(20) 
                self.t1 = threading.Timer(self.wait_time,self.AHE_meas_update)  #定时wait_time*5秒测量一组数据
            self.t1.start()

    def update_data_test(self):
        '''测试用，利用随机数来更新数据'''
        self.data.append([self.i_count,random.uniform(1,5)])
        self.i_count+=1  
    def update_test(self):
        '''循环更新数据，直至loop被设为0'''
        while(self.loop):

            if not self.t1:
                #当线程为空时，直接开始一个新的测量线程
                self.t1 = threading.Timer(self.wait_time,self.update_data_test)  #定时wait_time*5秒测量一组数据
            else:
                #仅当上一个线程结束后才进行下一个
                self.t1.join(20) 
                self.t1 = threading.Timer(self.wait_time,self.update_data_test)  #定时wait_time*5秒测量一组数据
            self.t1.start()   
    def AHE_meas(self):
        '''主程序：测量数据，并实时更新'''
        #连接各仪器并初始化
        self.initialization()
        
        #更新数据
        thread = threading.Thread(target=self.update)
        thread.start()

        '''反常霍尔测量'''
        def update_curve(curve):
            x=[date[0] for date in self.data]
            y=[date[1] for date in self.data]
            curve.setData(x,y) #更新图像数据

        """app=pg.mkQApp()
        win = pg.GraphicsWindow(show=True, title="Basic plotting examples")
        win.resize(1000,600)
        win.setWindowTitle('反常霍尔测量') """

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True) #开启抗锯齿
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        p1 = pg.plot(title="反常霍尔电阻测量")

        curve = p1.plot(pen='k',symbol='o',symbolPen='k',symbolBrush='r')
        #pen:线条颜色  symbol:数据点的形状 symbolPen:数据点边缘颜色   symbolBrush：数据点填充颜色

        p1.setLabel('left', "电阻", units='<font> &Omega;</font>')
        p1.setLabel('bottom', "磁场", units='Gs')
        p1.showGrid(x=True, y=True)

        timer = QtCore.QTimer()
        timer.timeout.connect(lambda :update_curve(curve))
        timer.start(50)

        if (sys.flags.interactive !=1) or not hasattr(QtCore,'PVQT_VERSION'):
            QtGui.QGuiApplication.instance().exec_()

        #将数据输出到文件
        self.path=self.fold+'/'+self.name#+'_number-{}_i-measure-{}.txt'.format(self.n_Magnet,self.i_output)
        np.savetxt(self.path,self.data) 
        self.loop=0 #停止测量
        self.t1.join(20) #等待最后一次测量结束
        self.rexit() #断开与各仪器连接
if __name__=='__main__':
    '''切换到当前文件所在目录'''
    current_path=os.path.abspath(__file__)
    current_fold = os.path.dirname(current_path)
    os.chdir(current_fold)
    A=control()
    A.name='kjt_8#_PHE.txt'
    A.AHE_meas()



