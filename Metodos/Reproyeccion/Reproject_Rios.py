def reproject_rios():

    import os,subprocess, time

    ruta = r'C:\Users\Diego\Desktop\Presentacion\protocolo\ori\20140812l8oli202_34'
    t = time.time()

    for i in os.listdir(ruta):
        
        if i.endswith('B1.TIF'):
            
            raster = os.path.join(ruta, i)
            salida = os.path.join(ruta, i[:-6]+'.img')
            match =  'C:\\Users\\Diego\\Desktop\\Presentacion\\protocolo\\geo\\20140812l8oli202_34\\20140812l8oli202_34_g_b1.img'

            cmd = ['rio', 'warp', raster, salida, '--co', 'driver=envi', '--like',  match]
            #cmd = ['rio', 'warp', inPut, outPut, '--like',  match]
            proc = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            stdout,stderr=proc.communicate()
            exit_code=proc.wait()

            print 'banda '+ str(i) + 'finalizada en  ' + str(time.time()-t)
            
    print 'imagen reproyectada en ' + str(time.time()-t)