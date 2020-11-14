# -*- coding: utf8 -*-
from switch2 import *
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtGui import QColor,QBrush
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton,
 QVBoxLayout,QGridLayout,QFormLayout,QMainWindow,QLineEdit
    ,QTableWidget,QHeaderView,QLabel,QDesktopWidget,QFileDialog,QTableWidgetItem)
import qdarkstyle
class Main_UI(QMainWindow):
    '''界面显示AHE测量数据，1.开始测量，2.停止测量'''
    def __init__(self,A):
        super().__init__()
        #参数设置
        self.fold='D:/DATA' #存储数据的目录，不存在则创建
        self.file_name='NewFile.txt' #文件名
        self.file_path=''
        self.begin_plot=1

        self.xlabel=['x','a']
        self.ylabel=['y','b']



        # 设置绘图背景
        pg.setConfigOption('background', 'w') #'w' #19232D
        pg.setConfigOption('foreground', 'k') #'k',d
        pg.setConfigOptions(antialias = True) #开启抗锯齿


        self.get_data=A.get_data #获取数据接口
        self.start_switch=A.start(A.switch_sweep_i_B) #翻转
        self.start_AHE=A.start_inf(A.AHE_update_one)
        self.exit_A=A.start(A.rexit)
        self.data_source=A


        self.init_ui()

        # 可以设置其他按钮点击 参考多行文本显示 然而不行 
        self.status = self.statusBar()
        self.status.showMessage("我在主页面～")        
        # 标题栏
        self.setWindowTitle("电输运测量系统")
        
    def init_ui(self):
        '''设置界面'''
        # self.setFixedSize(960,700)
        
        # 创建主窗口
        self.main_windows = QWidget()  
        self.main_windows.setWindowTitle('测量系统') #设置窗口标题
        # 创建主部件的网格布局
        self.main_layout = QGridLayout()  
        # 设置窗口主部件布局为网格布局
        self.main_windows.setLayout(self.main_layout)  

        #创建左上侧部件
        self.left_up_widget = QWidget()
        self.left_up_widget.setObjectName('left_up_widget') 
        QFormLayout.rowWrapPolicy=QFormLayout.WrapAllRows
        self.left_up_layout = QFormLayout()
        self.left_up_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        self.left_up_widget.setLayout(self.left_up_layout)

        # 创建左下侧部件
        self.left_widget = QWidget()  
        self.left_widget.setObjectName('left_down_widget')
        # 创建左侧部件的网格布局层
        self.left_layout = QGridLayout()  
        # 设置左侧部件布局为网格
        self.left_widget.setLayout(self.left_layout) 

        # 创建右侧部件
        self.right_widget = QWidget() 
        self.right_widget.setObjectName('right_widget')
        self.right_layout = QGridLayout()
        self.right_widget.setLayout(self.right_layout) 


        h1,h2=12,1
        w1,w2=3,4
        # 左侧部件在第0行第0列，占12行5列
        self.main_layout.addWidget(self.left_up_widget, 0, 0, h1, w1)
        # 下侧部件在第0行第6列，占12行3列
        self.main_layout.addWidget(self.left_widget, h1, 0, h2, w1+w2) 
        # 右侧部件在第0行第6列，占12行7列
        self.main_layout.addWidget(self.right_widget, 0, w1, h1, w2)
        # 设置窗口主部件
        self.setCentralWidget(self.main_windows)  

        #**********左上侧布局***********

        #5.设置参数
        self.name_AHE=['最小励磁电流','最大励磁电流','点数目n','励磁电流\n（n取0生效）','纵向电流','磁场最大变化','文件夹地址','文件名称']
        self.params_AHE=['i_Magnet_min','i_Magnet_max','n_Magnet','i_Magnet_list_fine','i_output','error']
        self.params_AHE=['self.data_source.{}'.format(pa) for pa in self.params_AHE]+['self.fold','self.file_name']

        self.params_type_AHE=[float,float,int,eval,float,float,str,str]
        self.set_params=self.creat_parames_table(self.name_AHE,self.params_AHE)

        #4.打开文件按钮
        self.bt_save_file=QPushButton('设置文件夹')
        self.bt_save_file.clicked.connect(self.f_set_file_path)
        #self.set_params.setCellWidget(len(data), 0, self.bt_save_file)

        self.left_up_layout.addWidget(self.set_params)
        self.left_up_layout.addWidget(self.bt_save_file)

        #6.设置表格

        self.name_switch=['循环次数','开始扫描电流(A)','结束扫描电流(A)','扫描脉冲个数','脉冲宽度(s)','脉冲与测量间隔(s)','辅助磁场大小(Oe)','测量电流大小(A)','文件夹地址','文件名称']
        self.params_switch=['loop_time','i_pulse_min','i_pulse_max','n_pulse','i_pulse_width','i_pulse_gap_time','B_Magnet_assist_list','i_output']

        self.params_type_switch=[int,float,float,int,float,float,eval,float,str,str]
        self.params_switch=['self.data_source.{}'.format(pa) for pa in self.params_switch]+['self.fold','self.file_name']
        
        self.set_params_switch=self.creat_parames_table(self.name_switch,self.params_switch)

        #设置表格的初始数据
        self.left_up_layout.addWidget(QLabel('switch参数设置'))
        self.left_up_layout.addWidget(self.set_params_switch)

        #
        # **********下侧布局***********

        #1.开始按钮
        self.bt_start = QPushButton("AHE开始") #开始测量
        self.bt_start.clicked.connect(self.start_AHE_bt)
        self.left_layout.addWidget(self.bt_start, 0, 1)

        self.bt_start = QPushButton("翻转开始") #开始测量
        self.bt_start.clicked.connect(self.start_switch_bt)
        self.left_layout.addWidget(self.bt_start, 0, 2)
        #2.结束按钮
        self.bt_stop = QPushButton("结束") #停止测量
        self.bt_stop.clicked.connect(self.rexit)
        self.left_layout.addWidget(self.bt_stop, 0, 3)

        #3.清除数据
        self.bt_clear = QPushButton("清除数据") #停止测量
        self.bt_clear.clicked.connect(self.clear_data)
        self.left_layout.addWidget(self.bt_clear, 0, 4)



        #***********右侧布局***********
        #1.标签栏
        self.label_right = QLabel("数据显示区域")
        self.right_layout.addWidget(self.label_right, 0, 6, 1, 7)
        #1.绘画框
        self.p1=pg.PlotWidget()#创建绘图控件
        self.right_layout.addWidget(self.p1, 1, 6, 5, 7) #将绘图控件添加到网格中

        #***********整体美化**********
        self.setWindowOpacity(0.9) # 设置窗口透明度
        self.main_layout.setSpacing(0)
        # 美化风格
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
          
        #def get_loop_time(self):
            #return (self.data_source.wait_time*(self.data_source.n_average*0.5+0.5)+1.2)*self.set_n_Magnet
    def creat_parames_table(self,name_list,params_list):
        '''创建参数表格'''
        set_params=QTableWidget(len(name_list),1) #初始化一个表格
        set_params.setVerticalHeaderLabels(name_list)
        set_params.horizontalHeader().hide() #隐藏表头
        #self.set_params.verticalHeader().hide() #隐藏表头
        #self.set_params.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) #填充整个界面
        set_params.setShowGrid(False) #不显示分割线
        for l in range(len(params_list)):
            item=QTableWidgetItem('{}'.format(eval(params_list[l])))
            #item.setBackground(QColor(255,255,255))
            #item.setForeground(QBrush(QColor(0,0,0)))
            set_params.setItem(l,0,item)
        return set_params
    def update_curve(self,curve):
        AHE_data=self.get_data()
        x=[date[0] for date in AHE_data]
        y=[date[1] for date in AHE_data]
        curve.setData(x,y) #更新图像数据

    def start_plot(self):
        '''绘制图像'''
        if(self.begin_plot):
            curve = self.p1.plot(pen='k',symbol='o',symbolPen='k',symbolBrush='r')
        #pen:线条颜色  symbol:数据点的形状 symbolPen:数据点边缘颜色   symbolBrush：数据点填充颜色

        self.p1.setLabel('bottom', self.xlabel[0], units=self.xlabel[1])
        self.p1.setLabel('left', self.ylabel[0], units=self.ylabel[1])
        self.p1.showGrid(x=True, y=True)
        self.p1.enableAutoRange('xy',True) #自动选定
        
        if(self.begin_plot):
            self.update_curve(curve)
            timer = QtCore.QTimer(self)
            timer.timeout.connect(lambda :self.update_curve(curve))
            timer.start(50)
        self.begin_plot=0


    def start_AHE_bt(self):
        #开始采集数据，开始绘图
        data=''
        try:
            for i in range(self.set_params.rowCount()-2):
                data=self.set_params.item(i,0).text()
                if(data):
                    exec(self.params_AHE[i]+'=self.params_type_AHE[i](data)')

            print('目录为'+eval(self.params_AHE[-2]))
            print('样品名为'+eval(self.params_AHE[-1]))
        except Exception as e:
            print('AHE输入参数错误')
            print('Reason:', e)
            return -1

        self.xlabel=['磁场','Gs']
        self.ylabel=['电阻','<font> &Omega;</font>']
        self.label_right.setText('反常霍尔测量')
        self.start_AHE()
        self.start_plot()
    def start_switch_bt(self):
        #开始采集数据，开始绘图
        data=[]
        try:
            for i in range(self.set_params_switch.rowCount()):
                data=self.set_params_switch.item(i,0).text()
                if(data):
                    exec(self.params_switch[i]+'=(self.params_type_switch[i])(data)')
            print('目录为'+eval(self.params_switch[-2]))
            print('文件为'+eval(self.params_switch[-1]))
        except Exception as e:
            print('switch输入参数错误')
            print('Reason',e)
            return -1
        self.data_source.pre_name=self.file_name
        self.data_source.fold=self.fold
        self.ylabel=['电阻','<font> &Omega;</font>']
        self.label_right.setText('翻转测量')
        if(self.data_source.loop_time<0):
            #self.start_switch=self.data_source.start(self.data_source.switch_up_down_i_sweep_B)
            self.xlabel=['次数','n']
        else:
            #self.start_switch=self.data_source.start(self.data_source.switch_sweep_i_B)
            self.xlabel=['脉冲电流','A']
        self.start_switch()
        self.start_plot()        
    def rexit(self):
        #保存数据，并退出
        #如果表格中参数不是空的，更新存储目录
        fold=self.set_params_switch.item(self.set_params_switch.rowCount()-2,0).text()
        name=self.set_params_switch.item(self.set_params_switch.rowCount()-1,0).text()
        if(fold):
            self.fold=fold
        if(name):
            self.file_name=name

        if not os.path.exists(self.fold):
            os.makedirs(self.fold)    
        #print('保存数据到：',self.fold+'/'+self.file_name.strip('.txt')+self.data_source.attach_name)

        #停止测量，并断开与仪器的连接
        self.exit_A()
        #保存数据
        #np.savetxt(self.fold+'/'+self.file_name.strip('.txt')+self.data_source.attach_name,self.get_data())
        self.data_source.save_data(name=self.data_source.attach_name,label=self.file_name.strip('.txt')+self.data_source.attach_name,pre_name=self.file_name,fold=self.fold)
    def clear_data(self):
        #清除数据
        self.data_source.data=[]


    def f_set_file_path(self):
        fileName, filetype = QFileDialog.getSaveFileName(self,
                                    "选取文件",
                                    self.fold+'/'+self.file_name,
                                    "All Files (*);;Text Files (*.txt)")
        if(fileName):
            self.file_name=fileName.split('/')[-1]
            print(self.file_name)
            self.fold='/'.join(fileName.split('/')[:-1])
            """             item=QTableWidgetItem(self.file_name)
            item.setBackground(QColor(255,255,255))
            item.setForeground(QBrush(QColor(0,0,0))) """
            self.set_params.setItem(self.set_params.rowCount()-1,0,QTableWidgetItem(self.file_name))
            self.set_params_switch.setItem(self.set_params_switch.rowCount()-1,0,QTableWidgetItem(self.file_name))

            item=QTableWidgetItem(self.fold)
            item.setBackground(QColor(255,255,255))
            item.setForeground(QBrush(QColor(0,0,0)))
            self.set_params.setItem(self.set_params.rowCount()-2,0,QTableWidgetItem(self.fold))
            self.set_params_switch.setItem(self.set_params_switch.rowCount()-2,0,QTableWidgetItem(self.fold))

        #self.set_file_path.setText(fileName)

def main():
    app = QApplication(sys.argv)
    A=control()

    #开始测量
    #A.start()
    
    #开始绘图
    U_AHE=Main_UI(A)
    U_AHE.show()
    if (sys.flags.interactive !=1) or not hasattr(QtCore,'PVQT_VERSION'):
        app.exec_()
    #停止测量
    A.rexit()




if __name__=='__main__':
    '''切换到当前文件所在目录'''
    current_path=os.path.abspath(__file__)
    current_fold = os.path.dirname(current_path)
    os.chdir(current_fold)
    #开始运行主程序
    main()
