#Ahora si que si!!!

parametros = {}


def nor(ruta):
    
    import os, re
    
    for i in os.listdir(ruta):
        
        if re.search('b[0-9].img', i):
            banda = os.path.join(ruta, i)
            banda_num = banda[-6:-4]
            print banda, ' desde nor'
            nor1(banda)
            
            if banda_num not in parametros.keys():
                lista_nor1bis = [nor1(banda, 22), nor1_bis(banda,11), nor1_bis(banda,22), nor1(banda,33), nor1_bis(banda,33)]
                for i in lista_nor1bis:
                    i