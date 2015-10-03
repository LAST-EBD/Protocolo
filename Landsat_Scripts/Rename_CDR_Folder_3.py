import os
from os import listdir
import glob
import time
import re
num = ['1', '2', '3', '4', '5', '6', '7', '8', '9'] 
lista = listacdr


def main():
        dire= r'C:\Users\Usuario\Desktop\pr\copia'
        os.chdir(dire)
        archivos=glob.glob('*')
        fecha=time.strftime("%d-%m-%Y")
        for i in listdir(dire):
            lista.append(i[:19])
            if re.search("^L\S[0-9]", i):
                sat = i[2]
                path =  i[3:6]
                row = i[7:9]
                fecha = time.strptime(i[9:13] + " " + i[13:16], '%Y %j')
                
                year = str(fecha.tm_year)
                month = str(fecha.tm_mon)
                day = str(fecha.tm_mday)
                
                #print i[:16]
                print "satelite: L", sat, "path:", path, "row:", row, "year:", fecha.tm_year, "month:", fecha.tm_mon, "day:", fecha.tm_mday
                print lista
                if i[:19] not in lista:
                    
                    if day in num and month in num:


                        if '5' in sat:
                            os.rename(i, year + "0" + month + "0" + day + "L" + sat + "tm" + path + "_" + row)
                            lista.append(i[:19])
                        else:
                            os.rename(i, year + "0" + month + "0" + day + "L" + sat + "etm" + path + "_" + row)
                            lista.append(i[:19])
                    elif month in num and day not in num:
                        if '5' in sat:
                            os.rename(i, year + "0" + month + day + "L" + sat + "tm" + path + "_" + row)
                            lista.append(i[:19])
                        else:
                            os.rename(i, year + "0" + month + day + "L" + sat + "etm" + path + "_" + row)
                            lista.append(i[:19])

                    elif month not in num and day in num:
                        if '5' in sat:
                            os.rename(i, year + month + "0" + day + "L" + sat + "tm" + path + "_" + row)
                            lista.append(i[:19])
                        else:
                            os.rename(i, year + month + "0" + day + "L" + sat + "etm" + path + "_" + row)
                            lista.append(i[:19])
                    else:
                        if '5' in sat:
                            os.rename(i, year + month + day + "L" + sat + "tm" + path + "_" + row)
                            lista.append(i[:19])
                        else:
                            os.rename(i, year + month + day + "L" + sat + "etm" + path + "_" + row)
                            lista.append(i[:19])

                
            
           
#print "encontrados"+ str(count) + "archivos de otro tipo
main()