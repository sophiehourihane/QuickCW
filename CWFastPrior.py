import numpy as np
import numba as nb
from numba import njit,prange
from numba.experimental import jitclass
from numba.typed import List

#import scipy as sc
#from scipy.stats.uniform import uni_pdf
#from scipy.stats.multivariate_normal import norm_pdf
from numba_stats import norm as norm_numba
from numba_stats import uniform as uniform_numba

################################################################################
#
#MY VERSION OF GETTING THE LOG PRIOR
#
################################################################################
class FastPrior:
    def __init__(self, pta):
        self.pta = pta
        self.param_names = List(pta.param_names)
        uniform_pars = List([])
        uf_lows = List([])
        uf_highs = List([])
        lin_exp_pars = List([])
        le_lows = List([])
        le_highs = List([])
        normal_pars = List([])
        nm_mus = List([])
        nm_sigs = List([])
        for par in self.pta.params:
            #print(par)
            if "Uniform" in par._typename:
                uniform_pars.append(par.name)
                uf_lows.append(float(par._typename.split('=')[1].split(',')[0]))
                uf_highs.append(float(par._typename.split('=')[2][:-1]))
            elif "LinearExp" in par._typename:
                lin_exp_pars.append(par.name)
                le_lows.append(float(par._typename.split('=')[1].split(',')[0]))
                le_highs.append(float(par._typename.split('=')[2][:-1]))
            elif "Normal" in par._typename:
                normal_pars.append(par.name)
                nm_mus.append(float(par._typename.split('=')[1].split(',')[0]))
                nm_sigs.append(float(par._typename.split('=')[2][:-1]))

        self.uniform_lows = np.array(uf_lows)
        self.uniform_highs = np.array(uf_highs)
        self.lin_exp_lows = np.array(le_lows)
        self.lin_exp_highs = np.array(le_highs)
        self.normal_mus = np.array(nm_mus)
        self.normal_sigs = np.array(nm_sigs)
        self.uniform_par_ids = np.array([self.param_names.index(u_par) for u_par in uniform_pars], dtype='int')
        self.lin_exp_par_ids = np.array([self.param_names.index(l_par) for l_par in lin_exp_pars], dtype='int')
        self.normal_par_ids = np.array([self.param_names.index(n_par) for n_par in normal_pars], dtype='int')

    def get_lnprior(self, x0):
        """wrapper to get ln prior"""
        return get_lnprior_helper(x0, self.uniform_par_ids, self.uniform_lows, self.uniform_highs,
                                      self.lin_exp_par_ids, self.lin_exp_lows, self.lin_exp_highs,
                                      self.normal_par_ids, self.normal_mus, self.normal_sigs)

    def get_sample(self, idx):
        """wrapper to quickly return random prior draw for the (idx)th parameter"""
        return get_sample_helper(idx, self.uniform_par_ids, self.uniform_lows, self.uniform_highs,
                                      self.lin_exp_par_ids, self.lin_exp_lows, self.lin_exp_highs,
                                      self.normal_par_ids, self.normal_mus, self.normal_sigs)

@njit()
def get_sample_helper(idx, uniform_par_ids, uniform_lows, uniform_highs,
                           lin_exp_par_ids, lin_exp_lows, lin_exp_highs,
                           normal_par_ids, normal_mus, normal_sigs):
    """jittable helper for prior draws"""
    if idx in uniform_par_ids:
        #iii = uniform_par_ids.index(idx)
        iii = np.min(np.nonzero(uniform_par_ids == idx)[0])
        return np.random.uniform(uniform_lows[iii], uniform_highs[iii])
    elif idx in lin_exp_par_ids:
        iii = np.min(np.nonzero(lin_exp_par_ids == idx)[0])
        return np.log10(np.random.uniform(10**lin_exp_lows[iii], 10**lin_exp_highs[iii]))
    else:
        iii = np.min(np.nonzero(normal_par_ids == idx)[0])
        return np.random.normal(normal_mus[iii], normal_sigs[iii])

@njit()
def get_lnprior_helper(x0, uniform_par_ids, uniform_lows, uniform_highs,
                           lin_exp_par_ids, lin_exp_lows, lin_exp_highs,
                           normal_par_ids, normal_mus, normal_sigs):
    """jittable helper for calculating the log prior"""
    log_prior = 0.0

    #loop through uniform parameters
    n = uniform_par_ids.size
    for i in range(n):
        low = uniform_lows[i]
        high = uniform_highs[i]
        value = x0[uniform_par_ids[i]]
        log_prior += np.log(uniform_numba.pdf(value, low, high-low))

    #loop through linear exponential parameters
    nn = lin_exp_par_ids.size
    for i in range(nn):
        low = lin_exp_lows[i]
        high = lin_exp_highs[i]
        value = x0[lin_exp_par_ids[i]]
        log_prior += np.log(((low <= value) & (value <= high)) * np.log(10) * 10 ** value / (10 ** high - 10 ** low)) #from enterprise

    #loop through normal parameters
    m = normal_par_ids.size
    for i in range(m):
        mu = normal_mus[i]
        sig = normal_sigs[i]
        value = x0[normal_par_ids[i]]
        log_prior += np.log(norm_numba.pdf(value, mu, sig ** 2))

    return log_prior
