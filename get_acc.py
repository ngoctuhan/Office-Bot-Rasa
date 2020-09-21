path = 'C:/Users/trung/Documents/Bot_Pho/resources/logs/DIET/20200920-005119/train\events.out.tfevents.1600537879.DESKTOP-P9HDQV8.16908.118.v2'

f=open(path,"rb")

lines=f.readlines()

for line in lines:
    print(line)
