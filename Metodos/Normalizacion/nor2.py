def nor2(banda, slope, intercept):
    
    '''Este metodo aplica la ecuacion de la recta de regresion a cada banda (siempre que los haya podido obtener), y posteriormente
    reescala los valores para seguir teniendo un byte (0-255)'''
      
    import numpy as np
    import rasterio, subprocess, os
    
    escena = r'C:\Users\Diego\Desktop\20051217L7etm202_34'
    banda_num = banda[-6:-4]
    outFile = os.path.join(escena, '_grn1' + banda_num + '.img')
    # Register GDAL format drivers and configuration options with a
    # context manager.
    with rasterio.drivers():

        # Read raster bands directly to Numpy arrays.
        #
        with rasterio.open(banda) as src:
            rs = src.read()

            NoData_rs = np.ma.masked_where(rs==255,rs)
            
            total = NoData_rs*slope+intercept
            min_msk = (total<0)
            max_msk = (total>255)
            total[min_msk] = 0
            total[max_msk] = 254

            profile = src.profile
            profile.update(type=rasterio.uint8, NoData = 255)

            with rasterio.open(outFile, 'w', **profile) as dst:
                dst.write(total.astype(rasterio.uint8))