import time, re
a = raw_input("introduzca la ruta: ")
from os import listdir
count = 0
satelites = []
counts = {}

for i in listdir(a):
    if re.search("^[0-9].*\w*", i):
        sat = i[8:10].upper()
        path =  i[-6:-3]
        row = i[-2:]
        year = i[:4]
        month = i[4:6]
        day = i[6:8]
        sensor = i[10:-6].lower()
        satelites.append(sat)
        counts[sat] = counts.get(sat,0) + 1
        print "satelite: ", sat, "sensor: ", sensor, "path:", path, "row:", row, "year:", year, "month:", month, "day:", day
    else:
        count += 1

for a, b in counts.items():
   #if a == "70":
       print a, b
print "encontrados", count, "archivos de otro tipo"