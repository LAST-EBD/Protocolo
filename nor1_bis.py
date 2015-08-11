def nor1_bis(banda, std):
    
    import rasterio, os
    import numpy as np
    from scipy.stats import linregress
    
    #Voy a poner la ruta a todas las bandas de la imagen de refrencia, pero habría que ver si no sería 
    #mejor dejar solo un dbf con los valores de las bandas (ahorro de espacio)
    
    #bandas
    path_b1 = r'C:\Users\Diego\Desktop\Landsat_8\20020718l7etm202_34\20020718l7etm202_34_grn1_b1.img'
    path_b2 = r'C:\Users\Diego\Desktop\Landsat_8\20020718l7etm202_34\20020718l7etm202_34_grn1_b2.img'
    path_b3 = r'C:\Users\Diego\Desktop\Landsat_8\20020718l7etm202_34\20020718l7etm202_34_grn1_b3.img'
    path_b4 = r'C:\Users\Diego\Desktop\Landsat_8\20020718l7etm202_34\20020718l7etm202_34_grn1_b4.img'
    path_b5 = r'C:\Users\Diego\Desktop\Landsat_8\20020718l7etm202_34\20020718l7etm202_34_grn1_b5.img'
    path_b7 = r'C:\Users\Diego\Desktop\Landsat_8\20020718l7etm202_34\20020718l7etm202_34_grn1_b7.img'
    
    #diccionario para evitar usar muchos if/elif
    dnorbandas = {'b1': path_b1, 'b2': path_b2, 'b3': path_b3, 'b4': path_b4, 'b5': path_b5, 'b7': path_b7}
    
    #mascaras
    #MASK_1 = r'C:\Users\Diego\Desktop\Landsat_8\MASK_1.img' #Areas Pseudo Invariantes
    equilibrada = r'C:\Users\Diego\Desktop\Landsat_8\equilibrada.img'
    mask_nubes = r'C:\Users\Diego\Desktop\Landsat_8\20051217l7eTM202_34_CM.img'
    #poly_inv_tipo = r'C:\Users\Diego\Desktop\Landsat_8\pol_inv_tipo.img'
    poly_inv_tipo_2 = r'C:\Users\Diego\Desktop\Landsat_8\pol_inv_2_tipo.img'
    
    with rasterio.open(equilibrada) as src:
        mask_eq = src.read()
    with rasterio.open(mask_nubes) as src:
        mask_nubes = src.read()
    with rasterio.open(poly_inv_tipo_2) as src:
        pias_2 = src.read()
    
    #aqui el resto de mascaras
    
    
    #entramos en el loop de las bandas
    
    banda_num = banda[-6:-4]
    if banda_num in dnorbandas.keys():
        with rasterio.open(banda) as src:
            current = src.read()
            #print i, current.mean(), current.min(), current.max()
        #Aqui con el diccionario nos aseguramos de que estamos comparando cada banda con su homologa del 20020718
        with rasterio.open(dnorbandas[banda_num]) as src:
            ref = src.read()
            #print dnorbandas[banda_num], ref.mean(), ref.min(), ref.max()
        #Ya tenemos todas las bandas de la imagen actual y de la imagen de referencia leidas como array

        #Aplicamos la mascara de las PIAs
        mask_curr_pia = np.ma.masked_where(mask_eq!=1,current)
        mask_ref_pia = np.ma.masked_where(mask_eq!=1,ref)
        mask_pias = np.ma.masked_where(mask_eq!=1,pias_2)
        
        #hemos aplicado la mascara y ahora guardamos una nueva matriz con la mascara aplicamos
        ref_PIA = np.ma.compressed(mask_ref_pia)
        current_PIA = np.ma.compressed(mask_curr_pia)
        pias2_PIA = np.ma.compressed(mask_pias)

        #Aplicamos la mascara de NoData
        NoData_current_mask = np.ma.masked_where(current_PIA==255,current_PIA)
        NoData_ref_mask = np.ma.masked_where(current_PIA==255,ref_PIA)
        NoData_pias2_PIA = np.ma.masked_where(current_PIA==255,pias2_PIA)
        ref_PIA_NoData = np.ma.compressed(NoData_ref_mask)
        current_PIA_NoData = np.ma.compressed(NoData_current_mask)
        PIA2_PIA_NoData = np.ma.compressed(NoData_pias2_PIA)

        #Esto sería la mascara de NoData de la imagen de referencia, en principio no la vamos a utilizar
        #img_20020718_b1_final = np.ma.masked_where(img_20020718_b1==255,img_20020718_b1)
        #img_20051217_b1_final = np.ma.masked_where(img_20020718_b1==255,img_20051217_b1)
        #f20020718_b1 = np.ma.compressed(img_20020718_b1_final)
        #f20051217_b1 = np.ma.compressed(img_20051217_b1_final)
        #Aplicamos la mascara de nubes

        #Realizamos la 1 regresion
        slope, intercept, r_value, p_value, std_err = linregress(current_PIA_NoData,ref_PIA_NoData)
        print 'slope: '+ str(slope), 'intercept:', intercept, 'r', r_value, 'N:', len(ref_PIA_NoData)

        #Ahora tenemos los parametros para obtener el residuo de la primera regresion y 
        #eliminar aquellos que son mayores de abs(11.113949)
        esperado = current_PIA_NoData * slope + intercept
        residuo = ref_PIA_NoData - esperado

        mask_current_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=int(std), current_PIA_NoData)
        mask_ref_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=int(std),ref_PIA_NoData)
        mask_pias2_PIA_NoData_STD = np.ma.masked_where(abs(residuo)>=int(std),PIA2_PIA_NoData)
        current_PIA_NoData_STD = np.ma.compressed(mask_current_PIA_NoData_STD)
        ref_PIA_NoData_STD = np.ma.compressed(mask_ref_PIA_NoData_STD)
        PIA2_PIA_NoData_STD = np.ma.compressed(mask_pias2_PIA_NoData_STD)

        #Hemos enmascarado los resiudos, ahora calculamos la 2 regresion
        slope, intercept, r_value, p_value, std_err = linregress(current_PIA_NoData_STD,ref_PIA_NoData_STD)
        print '++++++++++++++++++++++++++++++++++'
        print 'slope: '+ str(slope), 'intercept:', intercept, 'r', r_value, 'N:', len(ref_PIA_NoData_STD)
        print '++++++++++++++++++++++++++++++++++\n'
        
        #Ya tenemos los valores de la regresion para las pias con los poligonos equilibrados, ahora sacamos el count x tipo
        values = {}
        for i in range(1,10):
            mask_pia_= np.ma.masked_where(PIA2_PIA_NoData_STD != i, PIA2_PIA_NoData_STD)
            PIA2 = np.ma.compressed(mask_pia_)
            a = PIA2.tolist()
            values[i] = len(a)
        print values
    
    