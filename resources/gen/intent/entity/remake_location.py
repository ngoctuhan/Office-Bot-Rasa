fi = open("location_raw.txt", "r")

list_comma = ".,;')(*&^%$#@!~`:\"\\?><+-=_"
with open("location.txt", "w") as fo:
    for line in fi:
        line = line.replace("\n", "").strip()
        if line == "":
            continue
        for c in list_comma:
            line = line.replace(c, " ")
        while "  " in line:
            line = line.replace("  ", " ")
        line = line.lower()
        fo.write("{}\n".format(line))
        if "/" in line:
            line1 = line.replace("/", " xoẹt ")
            while "  " in line:
                line = line.replace("  ", " ")
            fo.write("{}\n".format(line1))
            line1 = line.replace("/", " trên ")
            while "  " in line:
                line = line.replace("  ", " ")
            fo.write("{}\n".format(line1))