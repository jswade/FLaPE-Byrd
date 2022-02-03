#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 13 23:49:40 2021
@author: mtd
"""

from numpy import reshape,concatenate,zeros,ones,triu,empty,arctan,tan,pi,std,mean,sqrt,var,cov,inf,polyfit,linspace,array,median
from scipy import stats,optimize
import matplotlib.pyplot as plt
import copy
import warnings

try:
    from offline.discharge import area
except ImportError:
    print('Warning in ReachObservations: No area module found. MetroMan style area calculations will be used')

class ReachObservations:    
        
    def __init__(self,D,RiverData,ConstrainHWSwitch=False,CalcAreaFit=0,dAOpt=0,Verbose=False):

        # CalcAreaFit=0 : don't calculate; CalcAreaFits=1 : use equal-spaced breakpoints; CalcAreaFits=2 : optimize breakpoints
	# dAOpt=0 : use MetroMan style calculation; dAopt=1 : use SWOT L2 style calculation
        
        self.D=D    
        self.CalcAreaFit=CalcAreaFit
        self.ConstrainHWSwitch=ConstrainHWSwitch
        self.Verbose=Verbose
        
        # assign data from input dictionary
        self.h=RiverData["h"]           
        self.w=RiverData["w"]
        self.S=RiverData["S"]
        self.h0=RiverData["h0"]
        self.sigh=RiverData["sigh"]
        self.sigw=RiverData["sigw"]
        self.sigS=RiverData["sigS"]    

        # calculate Area (i.e. H-W) fits for 3 sub-domain using EIV model a la SWOT
        if self.CalcAreaFit > 0:
            #caution! right now this only runs on reach 0 in this set. 
            self.CalcAreaFits()
        
        # constrain heights and widths to be self-consistent
        self.ConstrainHW()

        # create resahepd versions of observations
        self.hv=reshape(self.h, (self.D.nR*self.D.nt,1) )
        self.Sv=reshape(self.S, (self.D.nR*self.D.nt,1) )
        self.wv=reshape(self.w, (self.D.nR*self.D.nt,1) )
        
        # check area calculation option
        if dAOpt==1 and ( "area" not in globals() ):
             if self.Verbose:
                  print('Warning: ReachObservations tried to use SWOT-style area calcs, but no area function available. using MetroMan-style instead')
             dAOpt=0

        # calculate areas
        if dAOpt == 0:
             print('MetroMan-style area calculations')
             DeltaAHat=empty( (self.D.nR,self.D.nt-1) )
             self.DeltaAHatv = self.calcDeltaAHatv(DeltaAHat)
             self.dA= concatenate(  (zeros( (self.D.nR,1) ), DeltaAHat @ triu(ones( (self.D.nt-1,self.D.nt-1) ),0)),1 )
             self.dAv=self.D.CalcU() @ self.DeltaAHatv
        elif dAOpt == 1:
             print('SWOT-style area calculations')
             self.dA=empty( (self.D.nR,self.D.nt)   )
             for t in range(self.D.nt):
                 self.dA[0,t],hhat,what,dAUnc=area(self.h[0,t],self.w[0,t],self.area_fit)
             

    def calcDeltaAHatv(self, DeltaAHat):
        
        for r in range(0,self.D.nR):
            for t in range(0,self.D.nt-1):
                DeltaAHat[r,t]=(self.w[r,t]+self.w[r,t+1])/2 * (self.h[r,t+1]-self.h[r,t])
         
        # changed how this part works compared with Matlab, avoiding translating calcU
        return reshape(DeltaAHat,(self.D.nR*(self.D.nt-1),1) )
    
    def ConstrainHW(self):
        
        self.hobs=copy.deepcopy(self.h[0,:])
        self.wobs=copy.deepcopy(self.w[0,:])

        #range-normalize data
        x=self.hobs
        y=self.wobs
        x_range=max(x)-min(x)        
        x_mean=mean(x) 
        xn=(x-x_mean)/x_range
        y_range=max(y)-min(y)        
        y_mean=mean(y) 
        yn=(y-y_mean)/y_range
        
        #[m,b]=self.FitLOC(xn,yn)
        [m,b]=self.FitEIV(xn,yn)
        mo=-tan(pi/2-arctan(m))
 
        #projet w,h onto LOC or EIV
        hhatn=(yn-mo*xn-b)/(m-mo)
        whatn=m*hhatn+b

        #un-normalize data
        hhat=hhatn*x_range+x_mean
        what=whatn*y_range+y_mean

        hres=self.h[0,:]-hhat
        wres=self.w[0,:]-what

        self.stdh_LOChat=std(hres)
        self.stdw_LOChat=std(wres)

        if self.ConstrainHWSwitch:
             self.h[0,:]=hhat
             self.w[0,:]=what

    def plotHW(self):
        fig,ax = plt.subplots()
        
        if self.ConstrainHWSwitch:
            ax.scatter(self.hobs,self.wobs,marker='o')   
            ax.scatter(self.h[0,:],self.w[0,:],marker='o')   
        else: 
            ax.scatter(self.h[0,:],self.w[0,:],marker='o')   
            
        plt.title('WSE vs width for first reach')
        plt.xlabel('WSE, m')
        plt.ylabel('Width, m')      
        plt.show() 
        
    def plotdA(self):
        fig,ax = plt.subplots()
        ax.plot(self.D.t.T,self.dA[0,:])        
            
        plt.title('dA timeseries')
        plt.xlabel('Time, days')
        plt.ylabel('dA, m^2')      
        plt.show()       
        
    def plotHdA(self):
        fig,ax = plt.subplots()
        
        ax.scatter(self.h[0,:],self.dA[0,:],marker='o')   
            
        plt.title('dA vs WSE for first reach')
        plt.xlabel('WSE, m')
        plt.ylabel('dA, m')      
        plt.show()         

    def FitLOC(self,x,y):
        #references from Statistical Methods in Water Resources, by Helsel &
        #Hirsch, 1992. 

        sx=std(x)
        sy=std(y)

        mx=mean(x)
        my=mean(y)

        n=len(x)

        r=1/(n-1) * sum( (x-mx)/sx * (y-my)/sy ) # 8.6: Pearson's r

        b1=r*sy/sx #text below 10.7
        b1prime=1/r*sy/sx #text below 10.9

        b1doubleprime=sqrt(b1*b1prime) #slope: text above 10.10

        b0doubleprime=my-b1doubleprime*mx #intercept: comparing 10.10 with 10.9

        return b1doubleprime, b0doubleprime

    def FitEIV(self,x,y):
        #this is derived from fuller, for the ratio of variances model 1.3.7

        #compute sample variances and covariance
        mXX=var(x)
        mYY=var(y)
        Sigma=cov(x,y)
        mXY=Sigma[0,1]
 
        #this option has delta set to 1
        #beta1hat=((mYY-mXX)+( (mYY-mXX)**2 + 4*mXY**2   )**0.5 ) / (2*mXY)
        
        #this option lets you specify delta
        delta=1.0
        beta1hat=((mYY-delta*mXX)+( (mYY-delta*mXX)**2 + 4*delta*mXY**2   )**0.5 ) / (2*mXY)

        beta0hat=mean(y)-beta1hat*mean(x)

        return beta1hat, beta0hat

    def CalcAreaFits(self,r=0):

        warnings.filterwarnings("ignore", message="delta_grad == 0.0. Check if the approximated function is linear.")

        # this computes the SWOT-like height-width fit

 	# r : reach ID

        # outer level parameter vector:
        # po = Hb0,Hb1 i.e. WSE breakpoint 0, then WSE breakpoint 1
        # inner level parameter vector:
        # pi = p00, p01, p10, p11, p20,p21 i.e. p[domain 0][coefficient 0], p[domain 0][coefficient 1], p[domain 1][coefficient 0],...

        #0 check uncertainties
        if self.sigw<0:
             self.sigw=10 

        #1 choose initial parameters for outer loop
        WSEmin=min(self.h[r,:])
        WSEmax=max(self.h[r,:])
        WSErange=WSEmax-WSEmin
        WSErange=WSEmax-WSEmin
        init_params_outer=[WSEmin+WSErange/3, WSEmin+2*WSErange/3]

        #2 compute a solution where we set the breakpoints at 1/3 of the way through the domain
        ReturnSolution=True
        Jset,p_inner_set=SSE_outer(init_params_outer,self.h[r,:],self.w[r,:],ReturnSolution,self.sigh,self.sigw,self.Verbose)

        if self.Verbose:
            print('height-width fit for set breakpoints')
            plot3SDfit(self.h[r,:],self.w[r,:],p_inner_set,init_params_outer)

        #3 optimize both inner and outer loop simultaneously

        #3.1 parameter bounds
        nparams_outer=len(init_params_outer)
        lb=zeros(nparams_outer,)
        ub=zeros(nparams_outer,)

        lb[0]=WSEmin+WSErange*0.1
        ub[0]=WSEmin+WSErange*0.9
        lb[1]=WSEmin+WSErange*0.1
        ub[1]=WSEmin+WSErange*0.9

        param_bounds_outer=optimize.Bounds(lb,ub)

        #3.2 constrain breakpoints to be monotonic
        A=array([[1,-1]])
        constraint2=optimize.LinearConstraint(A,-inf,-0.1)    

        #3.3 nested solution to three-subdomain fit
        if self.CalcAreaFit == 2:
            #3.3.1 optimize breakpoints
            ReturnSolution=False
            res = optimize.minimize(fun=SSE_outer,
                    x0=init_params_outer,
                    args=(self.h[r,:],self.w[r,:],ReturnSolution,self.sigh,self.sigw,self.Verbose),
                    bounds=param_bounds_outer,
                    method='trust-constr',    
                    constraints=constraint2,
                    options={'disp':self.Verbose,'maxiter':1e2,'verbose':0})

            params_outer_hat=res.x

            #3.3.2 compute optimal fits for optimal breakpoints
            ReturnSolution=True
            [Jnest,params_inner_nest]=SSE_outer(params_outer_hat,self.h[r,:],self.w[r,:],ReturnSolution,self.sigh,self.sigw,self.Verbose)

            if self.Verbose:
                 print('height-width fit for nested optimization')
                 plot3SDfit(self.h[r,:],self.w[r,:],params_inner_nest,params_outer_hat)

        #3.3.3 determine whether to use optimal breakpoint solution or equal-spaced breakpoints 
        if self.CalcAreaFits == 2  and(res.success or (Jnest<Jset)):
             print('nested optimiztion sucess:',res.success)
             print('nested objective:',Jnest)
             print('set objective function:',Jset)
             print('using nested solution')
             self.Hbp=params_outer_hat
             self.HWparams=params_inner_nest
        else:
             self.Hbp=init_params_outer
             self.HWparams= p_inner_set

        #4 pack up fit parameter data matching swot-format 
        #4.0 initialize
        area_fit={}
        #4.1 set the dataset stats
        area_fit['h_variance']=array(var(self.h[r,:]))
        area_fit['w_variance']=array(var(self.w[r,:]))
        hwcov=cov(self.w[r,:],self.h[r,:])
        area_fit['hw_covariance']=hwcov[0,1]
        area_fit['med_flow_area']=array(0.) #this value estimated as described below 
        area_fit['h_err_stdev']=array(self.sigh)
        area_fit['w_err_stdev']=array(self.sigw)
        area_fit['h_w_nobs']=array(self.D.nt)

        #4.2 set fit_coeffs aka parameters aka coefficients - translate to SWOT L2 style format
        # pi = p00, p01, p10, p11, p20,p21 i.e. p[domain 0][coefficient 0], p[domain 0][coefficient 1], p[domain 1][coefficient 0],...
        nsd=3
        ncoef=2
        area_fit['fit_coeffs']=zeros((ncoef,nsd,1))
        for sd in range(nsd):
            for coef in range(ncoef):
                param_indx=sd*ncoef+coef
                area_fit['fit_coeffs'][coef,sd] = self.HWparams[param_indx]

        #4.3 set h_break
        area_fit['h_break']=zeros((4,1))
        area_fit['h_break'][0]=min(self.h[r,:])
        area_fit['h_break'][1]=self.Hbp[0]
        area_fit['h_break'][2]=self.Hbp[1]
        area_fit['h_break'][3]=max(self.h[r,:])

        #4.4 set w_break... though i do not think this get used so just initializing for now
        area_fit['w_break']=zeros((4,1))

        #4.5 calculate cross-sectional area at median value of H
        # a bit confusing, but we are centering the dA on the median H. so to get a dA value that
        # coresponds to Hbar, we set dA_hbar to zero, then evaluate the area fit at a value of 
        # Hbar. That returns the area value at median H that we use going forward
        Hbar=median(self.h[r,:])
        wbar=median(self.w[r,:])

        dA_Hbar,hhat,what,dAunc=area(Hbar, wbar, area_fit)

        area_fit['med_flow_area']=dA_Hbar

        #4.6 save fit data
        self.area_fit=area_fit

        return 

def ChooseInitParamsInner(h,w):
    #function to choose initial parameters describing SWOT-like height-width fit

    p1SD=polyfit(h,w,1) #slope and intercept for one sub-domain    

    init_params_inner=[p1SD[0],p1SD[1],p1SD[0],p1SD[1],p1SD[0],p1SD[1]]

    nparams_inner=len(init_params_inner)
    
    return init_params_inner,nparams_inner

def SetInnerParamBounds(nparams):
    #function to set initial parameter bounds describing SWOT-like height-width fit
    
    lb=zeros(nparams,)
    ub=zeros(nparams,)
      
    # slope values are 0,2,4. intercept values are 1,3,5
        
    # slope lower bound is zero, but upper bound is inf
    ub[0]=inf
    ub[2]=inf
    ub[4]=inf
    
    lb[0]=0 
    lb[2]=0
    lb[4]=0
    
    # intercept does not have bounds    
    lb[1]=-inf
    lb[3]=-inf
    lb[5]=-inf
    
    ub[1]=inf
    ub[3]=inf    
    ub[5]=inf
    
    return lb,ub

# define outer objective function, with inner objective function nested within
def SSE_outer(param_outer,h,w,ReturnSolution,sigh,sigw,Verbose):
    
    [init_params_inner,nparams_inner]=ChooseInitParamsInner(h,w)
    
    [lb,ub]=SetInnerParamBounds(nparams_inner)

    param_bounds_inner=optimize.Bounds(lb,ub)

    def SSE_inner(inner_params,xbreak,h,w,sigh,sigw):            
        
        i0=h<xbreak[0]                
        J0=(sigw**2 + inner_params[0]**2 * sigh**2)**-1*sum((h[i0]*inner_params[0]+inner_params[1]-w[i0])**2 )
        i1=(h>=xbreak[0]) & (h<xbreak[1])
        J1=(sigw**2 + inner_params[2]**2 * sigh**2)**-1*sum((h[i1]*inner_params[2]+inner_params[3]-w[i1])**2 )    
        i2=h>=xbreak[1]
        J2=(sigw**2 + inner_params[4]**2 * sigh**2)**-1*sum((h[i2]*inner_params[4]+inner_params[5]-w[i2])**2 )    
        
        J=J0+J1+J2    
        
        return J
 
    def cons0_f(x):        
        return x[0]*param_outer[0]+x[1]-x[2]*param_outer[0]-x[3] #this constraint requies this function to be equal to zero
    def cons1_f(x):        
        return x[2]*param_outer[1]+x[3]-x[4]*param_outer[1]-x[5] #this constraint requies this function to be equal to zero

    
    constraint0=optimize.NonlinearConstraint(cons0_f,0,0)
    constraint1=optimize.NonlinearConstraint(cons1_f,0,0)
        
    constraints=[constraint0,constraint1]    

    ShowDetailedOutput=Verbose
    if not ReturnSolution:
        ShowDetailedOutput=False

    res = optimize.minimize(fun=SSE_inner,
                    x0=init_params_inner,
                    args=(param_outer,h,w,sigh,sigw),
                    bounds=param_bounds_inner,
                    method='trust-constr',
                    constraints=constraints,
                    options={'disp':ShowDetailedOutput,'maxiter':1e3,'verbose':0})    

    if ReturnSolution:    
        return res.fun,res.x
    else:
        return res.fun

def plot3SDfit(h,w,params_inner,params_outer):
    fig,ax = plt.subplots()
    ax.scatter(h,w,marker='o')
    plt.title('WSE vs width ')
    plt.xlabel('WSE, m')
    plt.ylabel('Width, m')

    htest0=linspace(min(h),params_outer[0],10 )
    wtest0=params_inner[0]*htest0+params_inner[1]
    htest1=linspace(params_outer[0],params_outer[1],10)
    wtest1= params_inner[2]*htest1+params_inner[3]
    htest2=linspace(params_outer[1],max(h),10)
    wtest2= params_inner[4]*htest2+params_inner[5]

    plt.plot(htest0,wtest0,htest1,wtest1,htest2,wtest2)

    plt.show()
    return
