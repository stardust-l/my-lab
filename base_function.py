import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
class base_function(object):
    def __init__(self):
        self.xlabel=''
        self.ylabel=''
        self.end_name=''
        #文件存储路径
        self.pre_name='1#'
        self.attach_name=''
        self.fold='D:/DATA' 
        self.data_header=''
    def save_data(self,data,name='',attach_name='',fold='',label='',xlabel='',ylabel='',end_name='',data_header='',if_cover=1,if_label=1):
        '''保存现有的数据的txt文件，以及绘图，保存成png'''
        if not fold:
            fold=self.fold
        if not name:
            name=self.pre_name
        if not attach_name:
            attach_name=self.attach_name
        if not os.path.exists(fold):
            os.makedirs(fold)
        if(not xlabel):
            xlabel=self.xlabel
        if(not ylabel):
            ylabel=self.ylabel
        if(not end_name):
            end_name=self.end_name
        if not data_header:
            data_header=self.data_header
        if(len(data)<1):
            print('数据为空，不保存')
            return 0
        name=name.replace('.txt', '')
        name=name+attach_name.replace('.txt', '')+end_name
        if(not if_cover):
            #是否覆盖文件
            i=1
            add=''
            while(os.path.exists(fold+'/'+name+add+'.txt')):
                add='+%{}'.format(i)
                i+=1
            name=name+add
        if(if_label and (not label)):
            #当需要图例，且未给出图例，使用文件名当图例
            label=name
        print('保存到'+fold+'/'+name+'.txt')
        np.savetxt(fold+'/'+name+'.txt',data,header=data_header)
        x=[x[0] for x in data]
        y=[x[1] for x in data]
        plt.rcParams['font.sans-serif'] = ['SimHei']#显示中文
        plt.rcParams['axes.unicode_minus'] = False#显示负号
        if(len(data[0])<4):
            plt.plot(x,y,'ro-',label=label)
            plt.legend(loc='best',frameon=False)
            if(xlabel):
                plt.xlabel(xlabel)
            if(ylabel):
                plt.ylabel(ylabel)

            ax = plt.gca()
            ax.minorticks_on()#显示次刻度线
            ax.yaxis.get_major_formatter().set_powerlimits((0,1))#设置纵轴刻度为科学计数法
            
            plt.grid(b=True, which='major', lw='0.5', linestyle='-')
            plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        else:
            z=[x[3] for x in data]
            fig,ax=plt.subplots(1,2)
            ax[0].plot(x,y,'ro-',label=label+'_1')
            ax[0].legend(loc='best',frameon=False)
            ax[0].grid(b=True, which='major', lw='0.5', linestyle='-')
            ax[0].grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
            ax[0].minorticks_on()#显示次刻度线
            ax[0].yaxis.get_major_formatter().set_powerlimits((0,1))#设置纵轴刻度为科学计数法
            if(xlabel):
                ax[0].set_xlabel(xlabel)
            if(ylabel):
                ax[0].set_ylabel(ylabel)
            ax[1].plot(x,z,'ro-',label=label+'_2')
            ax[1].legend(loc='best',frameon=False)
            ax[1].grid(b=True, which='major', lw='0.5', linestyle='-')
            ax[1].grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
            ax[1].minorticks_on()#显示次刻度线
            ax[1].yaxis.get_major_formatter().set_powerlimits((0,1))#设置纵轴刻度为科学计数法
            if(xlabel):
                ax[1].set_xlabel(xlabel)
            if(ylabel):
                ax[1].set_ylabel(ylabel)
        if not os.path.exists(fold+'/fig'):
            os.makedirs(fold+'/fig')
        if not os.path.exists(fold+'/fig/fig_svg'):
            os.makedirs(fold+'/fig/fig_svg')

        plt.savefig(fold+'/fig/'+name+'.png')
        #plt.rasterization_zorder(0)
        plt.savefig(fold+'/fig/fig_svg/'+name+'.svg')
        plt.close()    
    def creat_list(self,l,name='',if_loop=0,if_repeat=0):
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
                    print(my_list)
                    print('输入的必须是[[10,100,5],[100,500,7]]的形式，括号内要有三个数')
                    assert 0
                my_list=[l[0][0]]
                
                for my_list_define in l:
                    list_new=np.linspace(my_list_define[0],my_list_define[1],my_list_define[2],endpoint=True)
                    if(len(list_new)>0 and my_list[-1]==list_new[0]):
                        #去除边界处的重复值
                        my_list=np.append(my_list,list_new[1:])
                    else:
                        my_list=np.append(my_list,list_new)

                my_list=list(my_list)#去除重复元素
            elif(type(l[0]) in [float,int]):
                #输入的是一维列表
                my_list=l
            else:
                print(my_list)
                print('输入格式有误，重新输入')
                assert 0
        else:
            print(my_list)
            print('输入格式有误，重新输入')
            assert 0
        if(if_loop):
            if(if_repeat):
                #是否去除重复点
                my_list=list(np.append(my_list,my_list[::-1]))
            else:
                my_list=list(np.append(my_list[:-1],my_list[::-1]))
        if(name):
            print(name,'列表为',my_list,sep='')
        return my_list

def mul_1000_list(x,mul_list=1000,mul_number=1000):
    if type(x)==list and type(x[0])==list:
        l=[]
        for i in x:
            l.append([i[0]*mul_number,i[1]*mul_number,i[2]])
        return l
    elif type(x)==list and type(x[0]) in [int,float]:
        return [i*mul_list for i in x]
    elif type(x) in [int,float]:
        return x*mul_number
def div_1000_float(x):
    return float(x)/1000
def div_1000_list(x,div_list=1000,div_number=1000):
    x=eval(x)
    if type(x)==list and (type(x[0]) in [int,float]):
        return [i/div_list for i in x]
    elif type(x)==list and type(x[0])==list:
        li=[]
        for i in x:
            li.append([i[0]/div_list,i[1]/div_list,i[2]])
        return li
    elif type(x) in [int,float]:
        return x/div_number
if __name__ == "__main__":
    a=[[0,1,2],[3,4,5]]
    text=base_function()
    text.save_data(data=a)