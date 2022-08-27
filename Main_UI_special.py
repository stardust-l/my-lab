# -*- coding: utf8 -*-
import pyqtgraph as pg
from PyQt5 import QtCore,QtWidgets
from PyQt5.QtGui import QColor,QBrush
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton,
 QVBoxLayout,QGridLayout,QFormLayout,QMainWindow,QLineEdit
    ,QTableWidget,QHeaderView,QLabel,QDesktopWidget,QFileDialog,QTableWidgetItem,QVBoxLayout,QTabWidget,QTabBar,QSplitter)
import qdarkstyle
from measure_special import *
from base_function import div_1000_float,div_1000_list,mul_1000_list
class Main_UI(QMainWindow):
    '''界面显示AHE测量数据，1.开始测量，2.停止测量'''
    def __init__(self,A):
        super().__init__()
        #参数设置
        #QMainWindow.sizePolicy=1
        self.fold='Z:/TEST' #存储数据的目录，不存在则创建
        if not os.path.exists('Z:/TEST'):
            self.fold='D:/DATA/TEST'
        self.file_name='NewFile.txt' #文件名
        self.xlabel=['x','a']
        self.ylabel=['y','b']
        self.data_source=A
        self.is_display=1

        # 设置绘图背景
        pg.setConfigOption('background', 'w') #'w' #19232D
        pg.setConfigOption('foreground', 'k') #'k',d
        pg.setConfigOptions(antialias = True) #开启抗锯齿


        #初始化界面
        self.init_ui()

        # 状态栏，以后可以看看能加上什么 
        self.status = self.statusBar()
        self.status.showMessage("我在主页面～")        
        # 标题栏
        self.setWindowTitle("电输运测量系统")
        
    def init_ui(self):
        '''设置界面'''      
        # 一、生成界面框架
        #设置主控件

        self.main_windows = QWidget()  
        
        self.main_windows.setWindowTitle('测量系统') #设置窗口标题        
        self.main_layout = QGridLayout()# 创建主部件的网格布局       
        self.main_windows.setLayout(self.main_layout) # 设置窗口主部件布局为网格布局 
        
        #splitter1 = QSplitter(Qt.Horizontal)
        #创建文件管理区域
        self.manage_file_widget = QWidget()
        self.manage_file_widget.setObjectName('manage_file_widget') #设置控件名字
        self.manage_file_layout = QFormLayout() #创建表单布局
        self.manage_file_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)#设置标签和输入框上下排列
        self.manage_file_widget.setLayout(self.manage_file_layout) #文件管理控件采用表单布局

        # 创建参数设置区,采取堆叠布局，即可切换页面,实现不同测量方式的切换
        self.set_parames_widget = QTabWidget()
        
        #self.set_parames_widget.setObjectName('set_parames_widget') #设置控件名字
        #self.set_parames_layout = QGridLayout()
        #self.set_parames_widget.setLayout(self.set_parames_layout) #参数设置区采用堆叠布局

        # 创建绘图区
        self.plot_widget = QWidget() 
        self.plot_layout = QGridLayout()
        self.plot_widget.setLayout(self.plot_layout) 

        # 创建按钮区
        self.button_widget = QWidget()
        self.button_layout = QGridLayout()          
        self.button_widget.setLayout(self.button_layout) 

        #将上面创建的四个区放入主控件中
        h1,h2=12,1
        w1,w2=2,5
        self.main_layout.addWidget(self.manage_file_widget, 0, 0, h2, w1)#主布局中加入管理文件控件
        self.main_layout.addWidget(self.set_parames_widget, h2, 0, h1, w1) #主布局中加入设置参数控件
        self.main_layout.addWidget(self.plot_widget, 0, w1, h1, w2)#主布局中加入绘图控件
        self.main_layout.addWidget(self.button_widget, h1, w1, h2, w2)#主布局中加入按钮控件
        self.main_windows.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        #self.manage_file_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        #self.set_parames_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        #self.plot_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding,)
        #self.button_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)
        
        #主控件设置为主窗口控件
        self.setCentralWidget(self.main_windows)  

        #完善各区域
        #**********文件设置区***********
        #设置文件夹，文件按钮
        self.set_fold,self.set_file_name=QLineEdit(self.fold),QLineEdit(self.file_name)
        self.manage_file_layout.addRow(QLabel('文件夹'),self.set_fold)
        self.manage_file_layout.addRow(QLabel('文件名'),self.set_file_name)
        self.bt_save_file=QPushButton('设置文件夹')#创建设置文件夹按钮
        self.bt_save_file.clicked.connect(self.f_set_file_path)#按钮绑定动作函数
        self.manage_file_layout.addWidget(self.bt_save_file)#按钮添加到文件区中
        #**********参数设置区***********
        #分界面
        '''AHE分界面'''       
        self.set_AHE()
        '''转角AHE界面'''
        self.set_AHE_rot()
        '''反常能斯特界面'''
        self.set_ANE()
        '''时间测量电阻分界面'''
        self.set_mea_R_by_time()
        '''二维磁场'''
        self.set_AHE_with_Hz()
        #切换界面动作绑定函数
        self.set_parames_widget.currentChanged.connect(self.display)
        #self.set_parames_widget.setContentsMargins(QtCore.QMargins(10,0,0,0))    
        #self.set_parames_widget.setStyleSheet('padding: -1')
        self.set_parames_widget.setStyleSheet("QTabWidget::pane { border: 0};")#隐藏边框
        #self.set_parames_widget.setStyleSheet('outline:0px')
        self.set_parames_widget.setFocusPolicy(0)#去除虚线框
        

        #**********绘图区***********
        #1.标签栏
        self.label_plot = QLabel("数据显示区域")
        self.plot_layout.addWidget(self.label_plot, 0, 0,1, 7)#, 
        #1.绘画框
        self.win=pg.GraphicsLayoutWidget()#pg.PlotWidget()#创建绘图控件
        self.plot_layout.addWidget(self.win, 1, 0,7, 7) #将绘图控件添加到网格中 , 7, 7
        self.p1=self.win.addPlot()#title='数据显示区域'
        #self.win.nextRow()
        self.p2=self.win.addPlot()#title='数据显示区域2'
        #self.win.removeItem(self.p2)
        self.start_plot()
        self.start_plot_2()
        #**********按钮区***********

        #1.结束按钮
        self.bt_stop = QPushButton("结束") #停止测量
        self.bt_stop.clicked.connect(lambda :self.data_source.start_new_thread(self.rexit))#连接到对应函数
        self.button_layout.addWidget(self.bt_stop, 0, 1)

        #2.清除数据
        self.bt_clear = QPushButton("清除数据") #停止测量
        self.bt_clear.clicked.connect(self.clear_data)
        self.button_layout.addWidget(self.bt_clear, 0, 2)

        #***********整体美化**********
        self.setWindowOpacity(0.9) # 设置窗口透明度
        self.main_layout.setSpacing(0)
        # 美化风格
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        #初始化
        self.display(0)   
            
    def set_AHE(self):
        #设定AHE分界面，包括参数，开始按钮以及其连接的参数更新与AHE测量开始函数
        #给出参数名称，参数对应变量名，参数应该显示的值，文本转为数据的函数,写到控件中后添加到参数设置区
        name=['循环次数','最小励磁电流(A)','最大励磁电流(A)','点数目n','励磁电流\n（n取0生效）\n-2为无回程','磁场列表\nn为-1生效\n-3有回程','纵向电流(mA)','磁场最大变化\n(Oe/0.5s)']
        params=['loop_time','i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','B_Magnet_list','i_mea','error']
        params_display=['loop_time','i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','B_Magnet_list','i_mea*1000','error']
        params_tran=[int,float,float,int,eval,eval,div_1000_float,float]
        params=['self.data_source.{}'.format(pa) for pa in params]
        params_display=['self.data_source.{}'.format(pa) for pa in params_display]

        AHE_widget=self.add_function_to_set_params(name,params_display,params,params_tran,self.data_source.start_inf(self.data_source.AHE))
        self.set_parames_widget.addTab(AHE_widget,'电阻-磁场')
    def set_AHE_rot(self):
        #设定AHE分界面，包括参数，开始按钮以及其连接的参数更新与AHE测量开始函数
        #给出参数名称，参数对应变量名，参数应该显示的值，文本转为数据的函数,写到控件中后添加到参数设置区
        name=['循环次数(-1无限)','最小励磁电流(A)','最大励磁电流(A)','点数目n','励磁电流\n（n取0生效）\n-2为无回程','磁场列表\nn为-1生效\n-3有回程','角度列表(°)','测量电流(mA)','磁场最大变化\n(Oe/0.5s)','细分数','电机速度','2182A积分时间\n0.01-50','是否恒定直流']
        params=['loop_time','i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','B_Magnet_list','angle_list','i_mea','error','subdivision','speed','rate','if_DC']
        params_display=['loop_time','i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','B_Magnet_list','angle_list','i_output*1000','error','subdivision','speed','rate','if_DC']
        params_tran=[int,float,float,int,eval,eval,eval,div_1000_float,float,int,int,float,int]
        params=['self.data_source.{}'.format(pa) for pa in params]
        params_display=['self.data_source.{}'.format(pa) for pa in params_display]
        params_display[-1]='1'
        AHE_widget=self.add_function_to_set_params(name,params_display,params,params_tran,self.data_source.start_inf(self.data_source.AHE_rot))
        self.set_parames_widget.addTab(AHE_widget,'转角AHE')
    def set_ANE(self):
        #给出参数名称，参数对应变量名，参数应该显示的值，文本转为数据的函数,写到控件中后添加到参数设置区
        name=['循环次数','最小励磁电流(A)','最大励磁电流(A)','点数目n','励磁电流\n（n取0生效）\n-2为无回程','加热电流(mA)','加热时间(s)','2182A积分时间\n 0.01-50','磁场最大变化\n(Oe/0.5s)']
        params=['loop_time','i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','i_heat','t_heat','rate','error']
        params_display=['loop_time','i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','i_heat*1000','t_heat','rate','error']
        params_tran=[int,float,float,int,eval,div_1000_float,float,float,float] 
        params=['self.data_source.{}'.format(pa) for pa in params]
        params_display=['self.data_source.{}'.format(pa) for pa in params_display]

        bt_rotation=QPushButton('停止加热')
        AHE_widget=self.add_function_to_set_params(name,params_display,params,params_tran,self.data_source.start_inf(self.data_source.ANE))
        
        def func_stop_heat():
            #停止加热
            self.data_source.temp_flag=0
        bt_rotation.clicked.connect(func_stop_heat)
        AHE_widget.children()[0].addWidget(bt_rotation)
        self.set_parames_widget.addTab(AHE_widget,'ANE')
    def set_mea_R_by_time(self):
        #设定正负脉冲分界面
        #给出参数名称，参数对应变量名，参数应该显示的值，文本转为数据的函数,写到控件中后添加到参数设置区
        name=['时间列表(s)\n(间隔大于等于0.1s)','脉冲大小(mA)','脉冲宽度(ms)\n0.6-12ms','测量电流(mA)','电压量程\n 0.01,0.1,1,10,100']
        params=['time_list','i_pulse','i_pulse_width','i_mea','V_range']
        params_display=['time_list','i_pulse*1000','i_pulse_width*1000','i_mea*1000','V_range']

        params_tran=[eval,div_1000_float,div_1000_float,div_1000_float,str]
        params=['self.data_source.{}'.format(pa) for pa in params]
        params_display=['self.data_source.{}'.format(pa) for pa in params_display]
        #params_display[0]='mul_1000_list(self.data_source.time_list)'
        params_widget=self.add_function_to_set_params(name,params_display,params,params_tran,self.data_source.start_inf(self.data_source.mea_R_by_time))
        self.set_parames_widget.addTab(params_widget,'电阻-时间')
    def set_AHE_with_Hz(self):
        #设定AHE分界面，包括参数，开始按钮以及其连接的参数更新与AHE测量开始函数
        #给出参数名称，参数对应变量名，参数应该显示的值，文本转为数据的函数,写到控件中后添加到参数设置区
        name=['循环次数','最小励磁电流(A)','最大励磁电流(A)','点数目n','励磁电流\n（n取0生效）\n-2为无回程','磁场列表\nn为-1生效\n-3有回程','纵向电流(mA)','细分数','电机速度','磁场最大变化\n(Oe/0.5s)','Hz(Oe)']
        params=['loop_time','i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','B_Magnet_list','i_mea','subdivision','speed','error','Hz']
        params_display=['loop_time','i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','B_Magnet_list','i_mea*1000','subdivision','speed','error','Hz']
        params_tran=[int,float,float,int,eval,eval,div_1000_float,int,int,float,float]
        params=['self.data_source.{}'.format(pa) for pa in params]
        params_display=['self.data_source.{}'.format(pa) for pa in params_display]

        AHE_widget=self.add_function_to_set_params(name,params_display,params,params_tran,self.data_source.start_inf(self.data_source.AHE_with_Hz))
        self.set_parames_widget.addTab(AHE_widget,'电阻-二维磁场')
    def display(self,i):
        #选择不同的功能页面，并进行一些参数的初始化设定
        if(self.data_source.loop==0):
            #在运行过程中切换界面不改变参数
            n_choose={'AHE':0,'AHE_rot':1,'ANE':2,'R_by_time':3,'AHE_with_Hz':4}
            #初始化
            self.data_source.end_name=''
            self.data_source.data_header=''
            self.data_source.attach_name=''
            self.display_s=''
            if i!=7:

                self.p2.hide()
            if i==n_choose['AHE']:
                #AHE
                self.xlabel=['磁场','Oe']
                self.ylabel=['电阻','<font> &Omega;</font>']   
                self.label_plot.setText('电阻-磁场测量')

                self.data_source.xlabel=r'$\rm H\ (Oe)$'
                self.data_source.ylabel=r'$\rm R_H\ (\Omega)$'         
                
            elif i==n_choose['AHE_rot']:
                #转角AHE
                self.xlabel=['磁场','Oe']
                self.ylabel=['电阻','<font> &Omega;</font>']   
                self.label_plot.setText('转角AHE')
                self.data_source.xlabel=r'$\rm H\ (Oe)$'
                self.data_source.ylabel=r'$\rm R\ (\Omega)$'  
                self.data_source.data_header='H(Oe) R(Omega)'#保存数据的注释行，表明测量的物理量
                #self.data_source.end_name='+HARM1'
            elif i==n_choose['ANE']:
                #转角能斯特
                #转角电阻  
                self.xlabel=['磁场','Oe']
                self.ylabel=['电压','V']   
                self.label_plot.setText('ANE测量')
                self.data_source.xlabel=r'$\rm H\ (Oe)$'
                self.data_source.ylabel=r'$\rm V\  (V)$'  
                self.data_source.data_header='H(Oe) V(V)'#保存数据的注释行，表明测量的物理量 
            elif i==n_choose['R_by_time']:
                self.xlabel=['时间','s']
                self.ylabel=['电阻','<font> &Omega;</font>']   
                self.label_plot.setText('电阻-时间')

                self.data_source.xlabel=r'$\rm t(s)$'
                self.data_source.ylabel=r'$\rm R_H\ (\Omega)$' 
                self.data_source.data_header='Time(s) R(Omega)'#保存数据的注释行，表明测量的物理量
            if i==n_choose['AHE_with_Hz']:
                #AHE
                self.xlabel=['磁场','Oe']
                self.ylabel=['电阻','<font> &Omega;</font>']   
                self.label_plot.setText('电阻-二维磁场测量')

                self.data_source.xlabel=r'$\rm H\ (Oe)$'
                self.data_source.ylabel=r'$\rm R_H\ (\Omega)$'   
            #更新图像坐标轴标签，自动确定坐标轴范围
            self.p1.setLabel('bottom', self.xlabel[0], units=self.xlabel[1])
            self.p1.setLabel('left', self.ylabel[0], units=self.ylabel[1])

    def update_curve(self,curve):
        AHE_data=self.data_source.data
        x=[date[0] for date in AHE_data]
        y=[date[1] for date in AHE_data]
        curve.setData(x,y) #更新图像数据
        try:
            self.p1.setTitle(self.display_s)#,color='008080',size='12pt'
        except:
            pass

    def start_plot(self):
        '''绘制图像'''
        curve = self.p1.plot(pen='k',symbol='o',symbolPen='k',symbolBrush='r')
        #pen:线条颜色  symbol:数据点的形状 symbolPen:数据点边缘颜色   symbolBrush：数据点填充颜色

        self.p1.setLabel('bottom', self.xlabel[0], units=self.xlabel[1])
        self.p1.setLabel('left', self.ylabel[0], units=self.ylabel[1])
        self.p1.showGrid(x=True, y=True)
        self.p1.enableAutoRange('xy',True) #自动选定
        
        self.update_curve(curve)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(lambda :self.update_curve(curve))
        timer.start(50)
    def update_curve_2(self,curve):
        data=self.data_source.data
        if(len(data)>=1 and len(data[0])>=4):
            x=[date[0] for date in data]
            y=[date[3] for date in data]
            curve.setData(x,y) #更新图像数据
        else:
            pass
    def start_plot_2(self):
        '''绘制图像'''
        curve = self.p2.plot(pen='k',symbol='o',symbolPen='k',symbolBrush='r')
        #pen:线条颜色  symbol:数据点的形状 symbolPen:数据点边缘颜色   symbolBrush：数据点填充颜色

        self.p2.setLabel('bottom', 'H', units='Oe')
        self.p2.setLabel('left', '二次谐波电压', units='V')
        self.p2.showGrid(x=True, y=True)
        self.p2.enableAutoRange('xy',True) #自动选定
        
        self.update_curve(curve)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(lambda :self.update_curve_2(curve))
        timer.start(50)
       
    def rexit(self):
        #保存数据，并退出
        #如果表格中参数不是空的，更新存储目录
        fold=self.set_fold.text()
        name=self.set_file_name.text()
        if(fold):
            self.fold=fold
        if(name):
            self.file_name=name
        self.data_source.pre_name=self.file_name
        self.data_source.fold=self.fold

        if not os.path.exists(self.fold):
            os.makedirs(self.fold)    
        #print('保存数据到：',self.fold+'/'+self.file_name.strip('.txt')+self.data_source.attach_name)
        #停止测量，并断开与仪器的连接
        #self.exit_A()
        if(not self.data_source.loop):
            self.data_source.rexit()
            time.sleep(3)
            self.data_source.close_all()
        self.data_source.loop=0
        time.sleep(3)
        #保存数据
        #np.savetxt(self.fold+'/'+self.file_name.strip('.txt')+self.data_source.attach_name,self.get_data())
        self.data_source.save_data(self.data_source.data)
        #self.data_source.save_data(name=self.data_source.attach_name,label=self.file_name.strip('.txt')+self.data_source.attach_name,pre_name=self.file_name,fold=self.fold)
    def clear_data(self):
        #清除数据
        self.data_source.data=[]

    def f_set_file_path(self):
        fold=self.set_fold.text()
        name=self.set_file_name.text()
        if(fold):
            self.fold=fold
        if(name):
            self.file_name=name        
        fileName, filetype = QFileDialog.getSaveFileName(self,
                                    "选取文件",
                                    self.fold+'/'+self.file_name,
                                    "All Files (*);;Text Files (*.txt)")
        if(fileName):
            self.file_name=fileName.split('/')[-1]
            print(self.file_name)
            self.fold='/'.join(fileName.split('/')[:-1])

            self.set_fold.setText(self.fold)
            self.set_file_name.setText(self.file_name)
            self.data_source.pre_name=self.file_name
            self.data_source.fold=self.fold
    def add_function_to_set_params(self,name_list,params_display_list,params_list,params_tran,func_start):
        #生成一个展示并可以修改参数的控件,由参数表格和开始按钮两部分组成
        #参数表格
        function_widget=QWidget()
        function_layout = QGridLayout()
        function_widget.setLayout(function_layout) 
        set_params_tabel=self.creat_parames_table(name_list,params_display_list)
        function_layout.addWidget(set_params_tabel)
        #开始按钮，连接参数读取、测量函数开始两个模块
        bt_start=QPushButton('开始测量')#创建设置文件夹按钮
        bt_start.clicked.connect(lambda:self.creat_start_bt(func_start=func_start,params_list=params_list,params_tran=params_tran,set_params_tabel=set_params_tabel))#按钮绑定动作函数
        function_layout.addWidget(bt_start)
        #美化开始按钮
        #bt_start.setStyleSheet('''QPushButton{background:#6DDF6D;border-radius:5px;}QPushButton:hover{background:green;}''')
        #bt_start.setFixedSize(15,15)
        return function_widget
    def update_params(self,params_list,params_tran,set_params_tabel):
        #更新表格数据到测量类的变量

        try:
            #更新标签页       
            #print(self.set_parames_widget)                
            #print(self.set_parames_widget.currentIndex())
            self.display(self.set_parames_widget.currentIndex())

            data=[]
            for i in range(set_params_tabel.rowCount()):
                data=set_params_tabel.item(i,0).text()#从表格中读取数据，非空的话传递给变量
                if(data):
                    exec(params_list[i]+'=(params_tran[i])(data)')   

        except Exception as e:
            print('输入参数错误')
            print('细节:',e)
            
            import traceback
            traceback.print_exc()
            self.data_source.loop=0
            assert 0       
    def creat_start_bt(self,func_start,params_list,params_tran,set_params_tabel):
        #开始采集数据，开始绘图

        try:
            fold=self.set_fold.text() #从文本框中读入文件夹以及文件名
            name=self.set_file_name.text()
            if(fold):
                self.fold=fold                       
            if(name):
                self.file_name=name
            self.data_source.fold=self.fold #将文件名传递给测量类，以便最后保存文件
            self.data_source.pre_name=self.file_name
            print('目录为'+self.fold)
            print('文件名为'+self.file_name)                       
            
        except Exception as e:
            print('输入文件参数错误')
            print('细节:',e)
            self.data_source.loop=0
            return -1
        try:
            self.update_params(params_list,params_tran,set_params_tabel)
        except:
            return -1
            
        self.p1.enableAutoRange('xy',True) #自动确定范围
        self.p2.enableAutoRange('xy',True)
        
        func_start()                
    def creat_parames_table(self,name_list,params_list):
        '''创建参数表格'''
        set_params=QTableWidget(len(name_list),1) #初始化一个表格
        set_params.setVerticalHeaderLabels(name_list)
        set_params.horizontalHeader().hide() #隐藏表头
        #set_params.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        for i in range(len(name_list)):
            #随内容分配行高
            set_params.verticalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        #set_params.verticalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) 
        #set_params.verticalHeader().hide() #隐藏表头
        #set_params.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) #填充整个界面
        set_params.setShowGrid(False) #不显示分割线
        for l in range(len(params_list)):
            item=QTableWidgetItem('{}'.format(eval(params_list[l])))
            #item.setBackground(QColor(255,255,255))
            #item.setForeground(QBrush(QColor(0,0,0)))
            set_params.setItem(l,0,item)

        return set_params

def main():
    app = QApplication(sys.argv)
    A=measure()
    
    #开始绘制界面
    U_AHE=Main_UI(A)
    U_AHE.resize(960,600)
    U_AHE.show()
    
    #不关闭则界面一直存在
    if (sys.flags.interactive !=1) or not hasattr(QtCore,'PVQT_VERSION'):
        app.exec_()
    #停止测量
    A.rexit(s_quit='界面关闭')


if __name__=='__main__':
    '''切换到当前文件所在目录'''
    current_path=os.path.abspath(__file__)
    current_fold = os.path.dirname(current_path)
    os.chdir(current_fold)
    #开始运行主程序
    main()
