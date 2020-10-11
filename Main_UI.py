from AHE_measure import *
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout,QGridLayout,QMainWindow,QTableWidget

class Main_UI(QMainWindow):
    '''主要用于画图，TODO：添加界面'''
    def __init__(self,A):
        super().__init__()
        #参数设置
        self.fold='data' #存储数据的目录，不存在则创建
        self.file_name='NewFile' #文件名



        # 设置绘图背景
        pg.setConfigOption('background', '#19232D') #'w'
        pg.setConfigOption('foreground', 'd') #'k'
        pg.setConfigOptions(antialias = True) #开启抗锯齿


        self.get_data=A.get_data #获取数据接口
        self.start_A=A.start
        self.exit_A=A.rexit

        self.init_ui()

        # 可以设置其他按钮点击 参考多行文本显示 然而不行 
        self.status = self.statusBar()
        self.status.showMessage("我在主页面～")        
        # 标题栏
        self.setWindowTitle("反常霍尔测量")
        


    def init_ui(self):

        # self.setFixedSize(960,700)
        
        # 创建主窗口
        self.main_windows = QWidget()  
        self.main_windows.setWindowTitle('反常霍尔测量') #设置窗口标题
        # 创建主部件的网格布局
        self.main_layout = QGridLayout()  
        # 设置窗口主部件布局为网格布局
        self.main_windows.setLayout(self.main_layout)  

        # 创建左侧部件
        self.left_widget = QWidget()  
        self.left_widget.setObjectName('left_widget')
        # 创建左侧部件的网格布局层
        self.left_layout = QGridLayout()  
        # 设置左侧部件布局为网格
        self.left_widget.setLayout(self.left_layout) 

        # 创建右侧部件
        self.right_widget = QWidget() 
        self.right_widget.setObjectName('right_widget')
        self.right_layout = QGridLayout()
        self.right_widget.setLayout(self.right_layout) 

        # 左侧部件在第0行第0列，占12行5列
        self.main_layout.addWidget(self.left_widget, 0, 0, 12, 5) 
        # 右侧部件在第0行第6列，占12行7列
        self.main_layout.addWidget(self.right_widget, 0, 5, 12, 7)
        # 设置窗口主部件
        self.setCentralWidget(self.main_windows)  


        # **********左侧布局***********

        #1.开始按钮
        self.bt_start = QPushButton("开始") #开始测量
        self.bt_start.clicked.connect(self.start)
        self.left_layout.addWidget(self.bt_start, 1, 0, 1, 5)

        #1.结束按钮
        self.bt_start = QPushButton("结束") #停止测量
        self.bt_start.clicked.connect(self.rexit)
        self.left_layout.addWidget(self.bt_start, 2, 0, 1, 5)

        #2.观察栏
        self.query_result = QTableWidget()
        self.left_layout.addWidget(self.query_result, 9, 0, 2, 5)
        self.query_result.verticalHeader().setVisible(False)

        #***********右侧布局***********
        #1.绘画框
        self.p1=pg.PlotWidget()#创建绘图控件
        self.right_layout.addWidget(self.p1, 0, 1, 5, 5) #将绘图控件添加到网格中
          

    def update_curve(self,curve):
        AHE_data=self.get_data()
        x=[date[0] for date in AHE_data]
        y=[date[1] for date in AHE_data]
        curve.setData(x,y) #更新图像数据
    def start_plot(self):

        '''反常霍尔测量'''

        curve = self.p1.plot(pen='k',symbol='o',symbolPen='k',symbolBrush='r')
        #pen:线条颜色  symbol:数据点的形状 symbolPen:数据点边缘颜色   symbolBrush：数据点填充颜色

        self.p1.setLabel('left', "电阻", units='<font> &Omega;</font>')
        self.p1.setLabel('bottom', "磁场", units='Gs')
        self.p1.showGrid(x=True, y=True)

        self.update_curve(curve)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(lambda :self.update_curve(curve))
        timer.start(50)


    def start(self):
        #开始采集数据，开始绘图
        self.start_A()
        self.start_plot()
    def rexit(self):
        #保存数据，并退出

        if not os.path.exists(self.fold):
            os.makedirs(self.fold)    
        file_path=self.fold+'/'+self.file_name

        #停止测量，并断开与仪器的连接
        self.exit_A()
        #保存数据
        np.savetxt(file_path,self.get_data())


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