from pyproj import Transformer
import numpy as np

def XY_1_to_XY_2(X, Y, epsg_in, epsg_out):
    """
    Convert coordinates defined in inProj projection, to outProj Projection
    """
    shape = X.shape
    X = X.flatten()
    Y = Y.flatten()
    transformer = Transformer.from_crs(int(epsg_in), int(epsg_out), always_xy=True)
    X2, Y2 = transformer.transform(X, Y)
    X2 = np.reshape(X2, shape)
    Y2 = np.reshape(Y2, shape)
    return X2, Y2