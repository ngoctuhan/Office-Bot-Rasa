list_entities = [
    "first",
    "amount",
    "product",
    "size",
    "last"
]

out_file_name = "output/order_gen.txt"
mode = "w"

import random as rd


def make_ett(name):
    file_list = open("entity/{}.txt".format(name), "r")
    ett = [line.replace("\n", "") for line in file_list.readlines()]
    file_list.close()
    if name in ["first", "last"]:
        return ett
    last = [""]
    first = [""]
    if name == "street":
        first = ["đường", "phố", "", ""]
    if name == "district":
        first = ["phường", ""]
    if name == "county":
        first = ["quận", ""]
    if name == "number":
        first = ["đến", "tới", "chỗ", "qua", "", "", "", "", ""]
    if name == "amount":
        last = ["cốc", "ly", "", "chiếc"]
    if name == "size":
        first = ["size", "sai", "", "cỡ", "loại"]
    new_ett = []
    for e in ett:
        if e == "":
            new_ett.append("")
        else:
            f = rd.choice(first)
            l = rd.choice(last)
            fm = f + " [{}]({})" + l
            new_ett.append(fm.format(e.lower(), name))
    return new_ett


if __name__ == "__main__":
    x = []
    for name in list_entities:
        x.append(make_ett(name))

    fo = open(out_file_name, mode)
    max_length = 0
    for e in x:
        max_length = max(max_length, len(e))
    n = len(x)
    m = max_length
    num_repeat = 20

    num_examples = 0
    for _ in range(num_repeat):
        tmp = x.copy()
        for i in range(n):
            rd.shuffle(tmp[i])
        for i in range(m):
            sent = ""
            for j in range(n):
                s = tmp[j][i % len(tmp[j])]
                c = " "
                sent += c + s + c
            while "  " in sent:
                sent = sent.replace("  ", " ")
            fo.write("- {}\n".format(sent.strip()))
            num_examples += 1
    print("Number of examples gen to `{}` = {}".format(out_file_name, num_examples))
