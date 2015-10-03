import time, re
a = raw_input("introduzca la ruta: ")
from os import listdir
count = 0
satelites = []
counts = {}

for i in listdir(a):
    if re.search("^L\S[0-9]", i):
        sat = i[:3]
        path =  i[3:6]
        row = i[7:9]
        fecha = time.strptime(i[9:13] + " " + i[13:16], '%Y %j')
        satelites.append(sat)
        counts[sat] = counts.get(sat,0) + 1
        print "satelite: ", sat, "path:", path, "row:", row, "year:", fecha.tm_year, "month:", fecha.tm_mon, "day:", fecha.tm_mday
    else:
        count += 1
		
for a, b in counts.items():
	print a, b
print "encontrados", count, "archivos de otro tipo"
