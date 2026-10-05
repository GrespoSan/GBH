"""Pine float comparisons round operands to nine fractional digits."""
import operator
import numpy as np
import pandas as pd
OPS={'Lt':operator.lt,'LtE':operator.le,'Gt':operator.gt,'GtE':operator.ge,'Eq':operator.eq,'NotEq':operator.ne}
def pine_cmp(left,right,op):
    def rounded(value):
        if isinstance(value,(float,np.floating)):
            return round(float(value),9)
        if isinstance(value,(pd.Series,np.ndarray)) and np.issubdtype(value.dtype,np.floating):
            return value.round(9)
        return value
    return OPS[op](rounded(left),rounded(right))
