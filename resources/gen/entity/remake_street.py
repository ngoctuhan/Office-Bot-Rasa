
f_street = open("street.txt", "r")
f_district = open("district.txt", "r")

streets = [line.replace("\n", "") for line in f_street]
f_district = [line.replace("\n", "") for line in f_district]

fo = open("street_rm.txt", "w")
for st in streets:
    if st in f_district:
        st = st + ":null"
    fo.write(st + "\n")