#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 21 04:50:53 2021

@author: mtd
"""

from numpy import inf,sqrt,mean,std,zeros_like,log

class FlowLaws:
    
    def __init__(self,dA,W,S,H):
        self.dA=dA
        self.W=W
        self.S=S       
        self.H=H       #plan is to switch these to Obs                
        
        self.params=[]
        self.init_params=[]                
        
        
        
class MWACN(FlowLaws):
    # this flow law is Manning's equation, wide-river approximation, area-formulation, 
    #   constant friction coefficient, no channel shape assumption: MWACN
    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)        
    def CalcQ(self,params):
        Q=1/params[0]*(params[1]+self.dA)**(5/3)*self.W**(-2/3)*self.S**(1/2)
        return Q
    def GetInitParams(self):
        #etc
        init_params=[.03, -min(self.dA)+1+std(self.dA)]
        return init_params
        #etc
    def GetParamBounds(self):
        param_bounds=( (.001, 1)  , (-min(self.dA)+1,inf) )
        return param_bounds
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
        dydp[0]=sum((2*sqrt(self.S)*(self.dA+params[1])**(5/3)*(Qt-(sqrt(self.S)*(self.dA+A)**(5/3))/(self.W**(2/3)*params[0])))/(W**(2/3)*params[0]**2))
        dydp[1]=-sum((10*sqrt(self.S)*(params[1]+self.dA)**(2/3)*(Qt-(sqrt(self.S)*(params[1]+self.dA)**(5/3))/(self.W**(2/3)*params[0])))/(3*W**(2/3)*params[0]))
        return dydp    
    def CalcQUn(self,params,sigh,sigw,order):
        if order == 1:
             QUnH=5/3*sqrt(2)*mean(self.W)*sigh/(params[1]+std(self.dA)) #1st order approximation
             QUnW_dA=5/3*sqrt(2)*std(self.H)*sigw/(params[1]+std(self.dA)) #1st order approximation
             QUnW_W=2/3*sigw/mean(self.W)
             QUnW=(QUnW_W**2+QUnW_dA**2)**0.5
             QUn=(QUnH**2+QUnW**2)**0.5
        else:
             QUn=inf
        return QUn,QUnH,QUnW


    
    
    
class MWAPN(FlowLaws):
    # this flow law is Manning's equation, wide-river approximation, area-formulation, 
    #   powerlaw  friction coefficient, no channel shape assumption: MWAPN
    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        n=params[0]*((params[1]+self.dA)/self.W)**params[2]
        Q=1/n*(params[1]+self.dA)**(5/3)*self.W**(-2/3)*self.S**(1/2)
        return Q
    def GetInitParams(self):
        #etc
        init_params=[.03, -min(self.dA)+1+std(self.dA),1]
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (.001, 1)  , (-min(self.dA)+1,inf), (-inf,inf) )
        return param_bounds               
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
        dydp[0]=sum()
        dydp[1]=sum()
        return dydp
    
    
    
    
class MWAVN(FlowLaws):
    # this flow law is Manning's equation, wide-river approximation, area-formulation, 
    #   hydraulic spatial variability approach, no channel shape assumption: MWAVN
    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        RHS=(1. + 5/6 * (self.W*params[2]/(params[1]+self.dA))**2 )
        if any(RHS <= 0):
            Q=inf
        else:
            n=params[0]*RHS
            Q=1/n*(params[1]+self.dA)**(5/3)*self.W**(-2/3)*self.S**(1/2)
        return Q
    def GetInitParams(self):
        #etc
        init_params=[.03, -min(self.dA)+1+std(self.dA),1]
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (.001, 1)  , (-min(self.dA)+1,inf), (-inf,inf) )
        return param_bounds               
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
        dydp[0]=sum()
        dydp[1]=sum()
        return dydp
    
    
    
    
class MWHCN(FlowLaws):
    # this flow law is Manning's equation, height only, constant n: MWHCN
    # params=n, H0
    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        Q=1/params[0]*(self.H-params[1])**(5/3)*self.W*self.S**(1/2)
        return Q
    def GetInitParams(self):
        #etc
        H0max=min(self.H)-0.1
        init_params=[.03,H0max-1.0] 
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (.001, 1.0)  , (-inf,min(self.H)-0.1) )
        return param_bounds  
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
        dydp[0]=sum()
        dydp[1]=sum()
        return dydp

    
    
    
class AHGW(FlowLaws):
    # this flow law is at-a-station hydraulic geometry for width
    #    Q=aW**b params=a,b
    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        Q=params[0]*self.W**params[1]
        return Q
    def GetInitParams(self):
        init_params=[0.5,0.25]
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (0.01,inf),(0.01,50.0) )
        return param_bounds               
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
#        dydp[0]=-2*sum( (Qt-params[0]*self.W**params[1])*self.W**params[1] )
#        dydp[1]=-2*sum( (Qt-params[0]*self.W**params[1])*params[0]*params[1]*self.W**(params[1]-1) )
        dydp[0]=-2*sum( (Qt-params[0]*self.W**params[1])*self.W**params[1] )
        dydp[1]=-2*sum( (Qt-params[0]*self.W**params[1])*(log(self.W**params[1]))*(params[0]*self.W**params[1]))
        return dydp

    
    
    
    
class AHGD(FlowLaws):
    # this flow law is at-a-station hydraulic geometry for depth
    #    it is identical to typical rating curves

    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        Q=params[0]*(self.H-params[1])**params[2]
        return Q
    def GetInitParams(self):
        H0max=min(self.H)-0.1
        init_params=[5.0,H0max-1.0,2.0]
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (0.01,inf),(-inf,min(self.H)-0.1),(0.01,10.) )
        return param_bounds               
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
        dydp[0]=sum()
        dydp[1]=sum()
        return dydp
    
    
    
    
class MOMMA(FlowLaws):
    # this is MOMMA, as written in eqns 9 and 10 of Frasson et al 2021
    # params=nb, Hb, B, r
    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        n=params[0]*(1+log( (params[1]-params[2] )/(self.H-params[2]) ) )
        Q=1/n*( (self.H-params[2])*(params[3]/(1+params[3])))**(5/3)*self.W*self.S**0.5
        return Q
    def GetInitParams(self):
        Bmax=min(self.H)-0.1
        init_params=[0.03,mean(H),Bmax-1.0,0.5]
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (0.01,inf),(min(self.H)+0.1,max(self.H)),(-inf,min(self.H)-0.1),(0.01,inf) )
        return param_bounds               
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
        dydp[0]=sum()
        dydp[1]=sum()
        return dydp
    
    
    
    
class MWHFN(FlowLaws):
    # this flow law is Manning's equation, height only, fixed n: MWHCN
    # params= H0
    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        Q=1/0.03*(self.H-params[0])**(5/3)*self.W*self.S**(1/2)
        return Q
    def GetInitParams(self):
        #etc
        H0max=min(self.H)-0.1
        init_params=[H0max-1.0] 
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (-inf,min(self.H)-0.1) )
        return param_bounds               
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
        dydp[0]=sum()
        dydp[1]=sum()
        return dydp
    
    
        
    
class AHGD_field(FlowLaws):
    # this flow law is at-a-station hydraulic geometry for depth
    #    intended to be used with depth - discharge field data
    #    for simplicity, redfine H as hydraulic depth
   #     note - in other functions, it is WSE 

    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        Q=params[0]*self.H ** params[1]
        return Q
    def GetInitParams(self):
        init_params=[1.0,0.5]
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (0.01,inf),(0.,inf) )
        return param_bounds               
    def Jacobian(self,params,Qt):
        dydp=zeros_like(params)
        dydp[0]=sum()
        dydp[1]=sum()
        return dydp
    
    
    
    
    
class PVK(FlowLaws):
    # this flow law is Prandtl von Karman equation
    # params= C, A0, y0
    def __init__(self,dA,W,S,H):
        super().__init__(dA,W,S,H)     
    def CalcQ(self,params):
        g=9.81
        Q=params[0]*(params[1]+self.dA)*(g*(params[1]+self.dA)/self.W*self.S )**0.5*log( (params[1]+self.dA)/self.W/params[2] )
        return Q
    def GetInitParams(self):
        #etc
        H0max=min(self.H)-0.1
        init_params=[10., -min(self.dA)+1+std(self.dA),1]
        return init_params       
    def GetParamBounds(self):
        #etc
        param_bounds=( (0.001, inf)  , (-min(self.dA)+1,inf), (0.001,inf) )
        return param_bounds               
    
