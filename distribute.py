import os
# Import the libraries
import matplotlib.pyplot as plt
import seaborn as sns
import io

list_name = []
list1= []
path = 'C:/Users/trung/Documents/Bot_Pho/data/nlu'
sum = 0
for file in os.listdir(path):
    file_path = os.path.join(path, file)
    # print(file)
    with io.open(file_path, encoding="utf-8") as eaf:
        # long_description = eaf.read()
        # print(long_description)
        lines = eaf.readlines()
        list1.append(len(lines))
        sum += list1[-1]
    list_name.append(file)

print(sum)
# matplotlib histogram
fig, axes = plt.subplots()
plt.bar([str(i) for i in range(len(list_name))],list1)

# Add labels
plt.title('Distribution of dataset')
plt.xlabel('Intent')
plt.ylabel('Number questions')
plt.show()