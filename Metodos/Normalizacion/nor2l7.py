def nor2(self, banda, slope, intercept):
    
        '''Este metodo aplica la ecuacion de la recta de regresion a cada banda (siempre que los haya podido obtener), y posteriormente
        reescala los valores para seguir teniendo un byte (0-255)'''
          
        path_nor_escena = os.path.join(self.nor, self.escena)
        if not os.path.exists(path_nor_escena):
            os.makedirs(path_nor_escena)
        banda_num = banda[-6:-4]
        outFile = os.path.join(path_nor_escena, self.escena + '_uint8_' + banda_num + '.img')
        
        with rasterio.drivers():
            
            with rasterio.open(banda) as src:
                rs = src.read()

                #NoData_rs = np.ma.masked_where(rs==255,rs)

                rs = rs*slope+intercept
                min_msk = (rs<0.5)
                max_msk = (rs>255)
                rs[min_msk] = 0.0
                rs[max_msk] = 255.0
                
                rs = np.around(rs)

                profile = src.meta
                profile.update(dtype=rasterio.uint8)

                with rasterio.open(outFile, 'w', **profile) as dst:
                    dst.write(rs.astype(rasterio.uint8))
    