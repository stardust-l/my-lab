# my-lab
实验室仪器控制
+ 实验仪器
6221 
2182A
F1208高斯计
KEPCO电流源
大恒光电的旋转台
SRS的锁相放大器
## 20220827
中间两年经历过比较大的修改，根据实际需要增加了许多功能

### 功能
1. 改变磁场测电阻（反常霍尔AHE,平面霍尔PHE，磁电阻MR）
2. 加固定磁场，转动角度测量电阻（转角磁电阻）
3. 加不同辅助磁场，改变脉冲电流，测量电阻（测量不同辅助场下的磁矩翻转，研究器件状态与加的脉冲电流的关系）
4. 加不同辅助磁场，加正负脉冲电流，测量电阻（测量不同辅助场下的磁矩翻转，模拟实际的正负读写）
5. 扫磁场测量一次以及二次谐波电压
6. 固定磁场，转角测量一次以及二次谐波电压
7. 改变测量电流，测量电阻随磁场的变化关系（主要用来测loop shift，获取无辅助磁场情况下电流产生的有效磁场大小）
8. 施加加热电流，稳定后测量热电压随磁场的关系（用于测量反常能斯特，界面在特殊测量功能中）

### 程序结构

1. intrument.py  放置与仪器直接通讯的底层控制函数，比如控制仪表加脉冲电流，旋转台转动，利用PID控制让电磁铁加到给定磁场等
2. measure.py  放置测量函数，比如改变磁场测电阻
3. Main_UI.py  界面相关
4. base_function.py 其他一些工具函数，比如传入数据和路径，自动绘图并保存；根据给定参数生成参数列表等

### 使用
运行对应的bat文件，改好参数后点击运行即可
## 20201014
### 三个功能
1. 改变磁场测电阻（反常霍尔AHE,平面霍尔PHE，磁电阻MR）
2. 加不同磁场，改变脉冲电流，测量电阻（测量不同辅助场下的磁矩翻转）
3. 加不同磁场，加脉冲电流，测量电阻（测量不同辅助场下的磁矩翻转，将循环次数设为负值即可切换到此模式）

### 其他
+ 拥有开始，停止，清除数据三个按键


## 反常霍尔测量
+ 通过励磁电流源控制磁场大小，利用四端法测量霍尔电阻，从而得到霍尔电阻随磁场大小变化的数据
+ 添加了界面，拥有开始和停止两个按键
