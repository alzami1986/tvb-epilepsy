import numpy
from sympy import Symbol, symbols, exp, solve, lambdify, Matrix, jacobian, MatrixSymbol, diff


def sym_vars(n_regions, vars_str, dims=1, ind_str="_"):

    vars_out = list()
    vars_dict = {}

    if dims == 1:

        for vs in vars_str:
            vars_out.append(numpy.array([Symbol(vs+ind_str+'%d' % i_n) for i_n in range(n_regions)]))
            vars_dict[vs] = vars_out[-1:]

    elif dims == 0:

        for vs in vars_str:
            vars_out.append(Symbol(vs))
            vars_dict[vs] = vars_out[-1:]


    elif dims == 2:

        for vs in vars_str:
            temp = []
            for i_n in range(n_regions):
                temp.append([Symbol(vs + ind_str + '%d' % i_n + ind_str + '%d' % j_n) for j_n in range(n_regions)])
            vars_out.append(numpy.array(temp))
            vars_dict[vs] = vars_out[-1:]
    else:
        raise ValueError("The dimensionality of the variables is neither 1 nor 2: " + str(dims))

    vars_out.append(vars_dict)

    return tuple(vars_out)



def eqtn_coupling(n, ix=None, jx=None, K="K"):

    # Only difference coupling for the moment.
    # TODO: Extend for different coupling forms

    x1, K, vars_dict = sym_vars(n, ["x1", "K"])
    w, vars_dict_w = sym_vars(n, ["w"], dims=2)
    vars_dict.update(vars_dict_w)

    if ix is None:
        ix = range(n)

    if jx is None:
        jx = range(n)

    i_n = numpy.ones((len(ix), 1))
    j_n = numpy.ones((len(jx), 1))

    x1 = numpy.expand_dims(x1.squeeze(), 1).T
    K = numpy.reshape(K, x1.shape)

    # Coupling                                                         from           to
    coupling = (K[:, ix]*numpy.sum(numpy.dot(w[ix][:, jx], numpy.dot(i_n, x1[:, jx])
                                                                      - numpy.dot(j_n, x1[:, ix]).T), axis=1)).tolist()

    return lambdify([x1, K, w], coupling, "numpy"), coupling, vars_dict


def eqtn_x0(n, zmode=numpy.array("lin"), K="K"):

    x1, z, x0cr, r, vars_dict = sym_vars(n, ["x1", "z", "x0cr", "r"])

    coupling, vars_dict_coupl = eqtn_coupling(n, K=K)[1:]
    vars_dict.update(vars_dict_coupl)

    if zmode == 'lin':
        x0 = (x1 + x0cr - (z + coupling) / 4.0) / r

    elif zmode == 'sig':
        x0 = (3.0 / (1.0 + numpy.exp(1) ** (-10.0 * (x1 + 0.5))) + x0cr - z + coupling) / r

    else:
        raise ValueError('zmode is neither "lin" nor "sig"')

    return lambdify([x1, z, x0cr, r, vars_dict[K], vars_dict["w"]], x0, "numpy"), x0, {"x1": x1, "z": z, "x0cr": x0cr, "r": r}


def eqtn_fx1_6d(n, x1_neg=True, slope="slope", Iext1="Iext1"):

    x1, z, x2, y1, slope, Iext1, a, b, tau1, vars_dict = sym_vars(n, ["x1", "z", "x2", "y1",
                                                                      "slope", "Iext1", "a", "b", "tau1"])

    # if_ydot0 = - self.a * y[0] ** 2 + self.b * y[0]
    if_ydot0 = - a * x1 ** 2 + b * x1  # self.a=1.0, self.b=-2.0

    # else_ydot0 = self.slope - y[3] + 0.6 * (y[2] - 4.0) ** 2
    else_ydot0 = slope - x2 + 0.6 * (z - 4.0) ** 2

    fx1 = (tau1 * (y1 - z + Iext1 + numpy.where(x1_neg, if_ydot0, else_ydot0) * x1)).tolist()

    return lambdify([x1, z, y1, x2, Iext1, slope, a, b, tau1], fx1, "numpy"), fx1, vars_dict


def eqtn_fx1_2d(n, x1_neg=True):

    x1, z, yc, slope, Iext1, a, b, tau1, vars_dict = sym_vars(n, ["x1", "z", "yc", "slope", "Iext1", "a", "b", "tau1"])

    # if_ydot0 = - self.a * y[0] ** 2 + self.b * y[0]
    if_ydot0 = - a * x1 ** 2 + b * x1  # self.a=1.0, self.b=-2.0

    # else_ydot0 = self.slope - 5 * y[0] + 0.6 * (y[2] - 4.0) ** 2
    else_ydot0 = slope - 5.0 * x1 + 0.6 * (z - 4.0) ** 2

    fx1 = (tau1 * (yc - z + Iext1 + numpy.where(x1_neg, if_ydot0, else_ydot0) * x1)).tolist()

    return lambdify([x1, z, yc, Iext1, slope, a, b, tau1], fx1, "numpy"), fx1, vars_dict


def eqtn_fy1(n):

    x1, y1, yc, d, tau1, vars_dict = sym_vars(n, ["x1", "y1", "yc", "d", "tau1"])

    fy1 = (tau1 * (yc - d * x1 ** 2 - y1)).tolist()

    return lambdify([x1, y1, yc, d, tau1], fy1, "numpy"), fy1, vars_dict


def eqtn_fz(n, zmode=numpy.array("lin"), x0="x0", K="K"):

    x1, z, x0, x0cr, r,  tau1, tau0, vars_dict = sym_vars(n, ["x1", "z", "x0", "x0cr", "r", "tau1", "tau0"])

    coupling, vars_dict_coupl = eqtn_coupling(n, K=K)[1:]
    vars_dict.update(vars_dict_coupl)

    if zmode == 'lin':
        fz = (tau1 * (4 * (x1 - r * x0 + x0cr) - z - coupling) / tau0).tolist()

    elif zmode == 'sig':
        fz = (tau1 * (3/(1 + numpy.exp(1.0) ** (-10.0 * (x1 + 0.5))) - r * x0 + x0cr - z - coupling) / tau0).tolist()
    else:
        raise ValueError('zmode is neither "lin" nor "sig"')

    return lambdify([x1, z, x0, x0cr, r, vars_dict[K], vars_dict["w"], tau1, tau0], fz, "numpy"), fz, vars_dict


def eqtn_fpop2(n, x2_neg=True, Iext2="Iext2"):

    x2, y2, z, g, Iext2, s, tau1, tau2, vars_dict = sym_vars(n, ["x2", "y2", "z", "g", "Iext2", "s", "tau1", "tau0"])

    # ydot[3] = self.tt * (-y[4] + y[3] - y[3] ** 3 + self.Iext2 + 2 * y[5] - 0.3 * (y[2] - 3.5) + self.Kf * c_pop2)
    fx2 = (tau1 * (-y2 + x2 - x2 ** 3 + Iext2 + 2.0 * g - 0.3 * (z - 3.5))).tolist()

    # if_ydot4 = 0
    if_ydot4 = 0
    # else_ydot4 = self.aa * (y[3] + 0.25)
    else_ydot4 = s * (x2 + 0.25)  # self.s = 6.0

    # ydot[4] = self.tt * ((-y[4] + where(y[3] < -0.25, if_ydot4, else_ydot4)) / self.tau)
    fy2 = (tau1 * (-y2 + numpy.where(x2_neg, if_ydot4, else_ydot4)) / tau2).tolist()

    return [lambdify([x2, y2, z, g, Iext2, tau1], fx2, "numpy"), \
            lambdify([x2, y2, s, tau1, tau2], fy2, "numpy")], [fx2, fy2], vars_dict


def eqtn_fg(n):

    gamma, tau1, vars_dict = symbols('gamma tau1')

    x1, g, gamma, tau1, vars_dict = sym_vars(n, ["x1", "g", "gamma", "tau1"])

    x1 = numpy.array([Symbol('x1_%d' % i_n) for i_n in range(n)])
    g = numpy.array([Symbol('g_%d' % i_n) for i_n in range(n)])

    #ydot[5] = self.tt * (-0.01 * (y[5] - 0.1 * y[0]))
    fg =(-tau1 * gamma * (g - 0.1 * x1)).tolist()

    return lambdify([x1, g, gamma, tau1], fg, "numpy"), fg, vars_dict


def eqtn_fparam_vars(n, pmode=numpy.array("const")):

    tau1, tau0, vars_dict = symbols('tau1 tau0')

    z, g, x0_var, slope_var, Iext1_var, Iext2_var, K_var, x0, slope, Iext1, Iext2, K, tau1, tau0, vars_dict \
        = sym_vars(n, ["z", "g", "x0_var", "slope_var", "Iext1_var", "Iext2_var", "K_var",
                                  "x0", "slope", "Iext1", "Iext2", "K", "tau1", "tau0"])

    #ydot[5] = self.tt * (-0.01 * (y[5] - 0.1 * y[0]))
    fx0 =(tau1 * (-x0_var + x0)).tolist()

    from tvb_epilepsy.tvb_api.epileptor_models import EpileptorDPrealistic
    slope_eq, Iext2_eq = EpileptorDPrealistic.fun_slope_Iext2(z, g, pmode, slope, Iext2)

    # slope
    # ydot[7] = 10 * self.tau1 * (-y[7] + slope_eq)
    fslope = (10.0 * tau1 * (-slope_var + slope_eq)).tolist()
    # Iext1
    # ydot[8] = self.tau1 * (-y[8] + self.Iext1) / self.tau0
    fIext1 = (tau1 * (-Iext1_var + Iext1) / tau0).tolist()
    # Iext2
    # ydot[9] = 5 * self.tau1 * (-y[9] + Iext2_eq)
    fIext2 = (5.0 * tau1 * (-Iext2_var + Iext2_eq)).tolist()
    # K
    # ydot[10] = self.tau1 * (-y[10] + self.K) / self.tau0
    fK = (tau1 * (-K_var + K) / tau0).tolist()

    return [lambdify([x0, x0_var, tau1], fx0, "numpy"),
            lambdify([z, g, slope, slope_var, tau1], fslope, "numpy"),
            lambdify([Iext1, Iext1_var, tau1, tau0], fIext1, "numpy"),
            lambdify([z, g, Iext2, Iext2_var, tau1], fIext2, "numpy"),
            lambdify([K, K_var, tau1, tau0], fK, "numpy")], \
           [fx0, fslope, fIext1, fIext2, fK], vars_dict


def eqnt_dfun(n_regions, model_vars, zmode=numpy.array("lin"), x1_neg=True, x2_neg=True, pmode=numpy.array("const")):

    f_lambda = []
    f_sym = []

    if model_vars == 2:

        fl, fs, symvars = eqtn_fx1_2d(n_regions, x1_neg) #sv_x1 = [x1, z, yc, slope, Iext1, a, b, tau1]
        f_lambda.append(fl)
        f_sym.append(fs)

        fl, fs, sv_z = eqtn_fz(n_regions, zmode) # sv_z = [x1, z, x0, x0cr, r, K, w, tau1, tau0]
        f_lambda.append(fl)
        f_sym.append(fs)

        #         [x1, z, yc, slope, Iext1, x0, x0cr, r, K, w, a, b, tau1, tau0]
        symvars.update(sv_z)

    elif model_vars == 6:

        fl, fs, symvars = eqtn_fx1_6d(n_regions, x1_neg)
        f_lambda.append(fl)
        f_sym.append(fs)

        fl, fs, vs_y1 = eqtn_fy1(n_regions)
        f_lambda.append(fl)
        f_sym.append(fs)
        symvars.update(vs_y1)

        fl, fs, vs_z = eqtn_fz(n_regions, zmode)
        f_lambda.append(fl)
        f_sym.append(fs)
        symvars.update(vs_z)

        fl, fs, vs_pop2 = eqtn_fpop2(n_regions, x2_neg)
        f_lambda += fl
        f_sym += fs
        symvars.update(vs_pop2)

        fl, fs, vs_g = eqtn_fg(n_regions)
        f_lambda.append(fl)
        f_sym.append(fs)
        symvars.update(vs_g)

    elif model_vars == 11:

        fl, fs, symvars = eqtn_fx1_6d(n_regions, x1_neg, "slope_var", "Iext1_var")
        f_lambda.append(fl)
        f_sym.append(fs)

        fl, fs, vs_y1 = eqtn_fy1(n_regions)
        f_lambda.append(fl)
        f_sym.append(fs)
        symvars.update(vs_y1)

        fl, fs, vs_z = eqtn_fz(n_regions, zmode)
        f_lambda.append(fl)
        f_sym.append(fs)
        symvars.update(vs_z)

        fl, fs, vs_pop2 = eqtn_fpop2(n_regions, x2_neg, "Iext2_var")
        f_lambda += fl
        f_sym += fs
        symvars.update(vs_pop2)

        fl, fs, vs_g = eqtn_fg(n_regions)
        f_lambda.append(fl)
        f_sym.append(fs)
        symvars.update(vs_g)

        fl, fs, vs_params_vars = eqtn_fparam_vars(n_regions, pmode)
        f_lambda += fl
        f_sym += fs
        symvars.update(vs_params_vars)


    return f_lambda, f_sym, symvars


def eqnt_jac(n_regions, model_vars, zmode=numpy.array("lin"), x1_neg=True, x2_neg=True, pmode=numpy.array("const")):

    dfun_sym, vars_dict = eqnt_dfun(n_regions, model_vars, zmode, x1_neg, x2_neg, pmode)[1:]

    dfun_sym = Matrix(dfun_sym)

    if model_vars == 2:

        x = [vars_dict['x1'], vars_dict['z']]

    elif model_vars == 6:

        x = Matrix([vars_dict['x1'], vars_dict['y1'], vars_dict['z'], vars_dict['x2'], vars_dict['y2'], vars_dict['g']])

    elif model_vars == 11:

        x = Matrix([vars_dict['x1'], vars_dict['y1'], vars_dict['z'], vars_dict['x2'], vars_dict['y2'], vars_dict['g'],
                    vars_dict['x0_var'], vars_dict['slope_var'], vars_dict['Iext1_var'], vars_dict['Iext2_var'],
                    vars_dict['K_var']])

    jac_sym = dfun_sym.jacobian(Matrix(x))

    jac_lambda = lambdify(x, jac_sym, "numpy")

    return jac_lambda, jac_sym, vars_dict