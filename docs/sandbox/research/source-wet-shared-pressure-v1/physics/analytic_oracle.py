"""Independent manufactured stable-linear-liquid oracle; no production imports."""
from fractions import Fraction as F
from decimal import Decimal as D, localcontext
from pathlib import Path
import math,json,time,hashlib
start=time.monotonic();checks=0

def ck(ok,label):
 global checks
 checks+=1
 if not ok:raise AssertionError(label)
def up(x):
 f=float(x)
 return F(math.nextafter(f,math.inf)) if F(f)<x else F(f)
def S(x):return F(math.ulp(float(up(x))))
def dec(x):return D(x.numerator)/D(x.denominator)
R=F(8.31446261815324);m=F(.018015268);v0=F(18,10**6);alpha=F(1,10**8);beta=F(1,10**14);eps=F(1,10**18);J=(F(800000),F(1300000));V0=F(.001);ev=F(1e-12);volumes=(V0-ev,V0,V0+ev);td=(F(300),F(340));pd=(F(600000),F(1600000));eT=F(1e-6)
def v(T,p):return v0+alpha*(T-320)-beta*(p-1000000)
def G(nl,N,T,p,V):return nl*v(T,p)+N*R*T/p-V
def root(nl,N,T,V):
 with localcontext() as ctx:
  ctx.prec=100
  b=nl*(v0+alpha*(T-320)+beta*1000000)-V
  return (dec(b)+(dec(b)**2+4*dec(nl*beta)*dec(N*R*T)).sqrt())/(2*dec(nl*beta))
def native(nl,ns,T,p,V):
 rho=float(m/v(T,p));lv=(float(nl)*float(m))/rho;nrt=math.fsum(ns)*float(R)*float(T);vg=nrt/float(p)
 return F(math.fsum((lv,vg,-float(V)))),F(float(float(m)/rho))
def bound(nl,ns,T):
 N=sum(map(F,ns),F());vl=v(T,J[1])-eps;vu=v(T,J[0])+eps;Wcap=2*(vu+eps);Wfloor=(vl-eps)/2;ck(Wfloor>0,'normal volume lower')
 rhomin=m/Wcap;A=F(float(float(nl)*float(m)));dA=abs(A-nl*m);Lmax=abs(A)/rhomin+S(abs(A)/rhomin);GL=nl*(eps+S(Wcap))+dA/rhomin+S(abs(A)/rhomin)
 nrt=F(math.fsum(ns)*float(R)*float(T));GG=abs(nrt-N*R*T)/J[0]+S(abs(nrt)/J[0]);Gmax=abs(nrt)/J[0]+S(abs(nrt)/J[0]);GS=2*S(Lmax+Gmax+volumes[-1]);gamma=GL+GG+GS
 return (vl,vu),gamma
A=(F(.25),(.125,.25,1e-12),F(320));B=(F(.25000001),(.125,.25000001,1e-12),F(321));cases=[('different',A,B),('reversed',B,A),('cancellation',A,A),('different_liquid',A,(F(.125),(.125,.25,1e-12),F(320)))];results=[]
for name,a,b in cases:
 parts=[]
 for nl,ns,T in (a,b):
  N=sum(map(F,ns),F());iv,gamma=bound(nl,ns,T);ck(nl*(v(T,J[0])-eps)+N*R*T/J[0]-volumes[-1]>=0 and nl*(v(T,J[1])+eps)+N*R*T/J[1]-volumes[0]<=0,'all V root signs')
  for j in range(25):
   p=J[0]+(J[1]-J[0])*j/24
   # Production pressure inputs are binary64; use the exactly represented probe.
   p=F(float(p))
   for V in volumes:
    gh,vh=native(nl,ns,T,p,V);ck(abs(vh-v(T,p))<=eps,'preregistered native ratio epsilon');ck(abs(gh-G(nl,N,T,p,V))<=gamma+abs(F(float(V))-V),'Gamma includes explicit V input projection')
  center=F(float(root(nl,N,T,V0)));Bup=max(abs(-tt*alpha+pp*beta) for tt in td for pp in pd);oldEP=F(1e-3);r0=max(oldEP,abs(center-J[0]),abs(J[1]-center));Lg=pd[1]/td[0]*(1+nl*Bup*pd[1]/(N*R*td[0]));g=r0+Lg*eT;ck(pd[0]<center-g<center+g<pd[1],'new continuation full domain');Lnew=(center+g)/(T-eT)*(1+nl*Bup*(center+g)/(N*R*(T-eT)));gold=oldEP+Lg*eT;Lold=(center+gold)/(T-eT)*(1+nl*Bup*(center+gold)/(N*R*(T-eT)));used=max(Lold,Lnew);ck(used>=Lold and Lnew>Lold,'no old L shrink wide J')
  for V in volumes:
   p0=root(nl,N,T,V);ck(dec(J[0])<=p0<=dec(J[1]),'independent Decimal root enclosure')
   for dt in (-eT,eT):ck(abs(root(nl,N,T+dt,V)-p0)<=dec(used*eT),'independent temperature root movement')
  parts.append((nl,N,T,iv,gamma,used))
 aa,bb=parts;numer=R*(aa[1]*aa[2]-bb[1]*bb[2]);gas=sorted((numer/J[0],numer/J[1]));dlo=aa[0]*aa[3][0]-bb[0]*bb[3][1]+gas[0];dhi=aa[0]*aa[3][1]-bb[0]*bb[3][0]+gas[1];c=min(x[1]*R*x[2]/J[1]**2 for x in parts);bound_report=max(abs(dlo),abs(dhi))/c;bound_full=bound_report+sum((x[5]*eT for x in parts),F())
 for V in volumes:
  for ta in (-eT,F(),eT):
   for tb in (-eT,F(),eT):ck(abs(root(aa[0],aa[1],aa[2]+ta,V)-root(bb[0],bb[1],bb[2]+tb,V))<=dec(bound_full),'independent complete joint root bound')
 results.append({'case':name,'Gamma_m3':[float(x[4]) for x in parts],'reported_root_bound_pa':float(bound_report),'full_root_bound_pa':float(bound_full)})
# Fixed negatives: narrow wrong support and independent-volume cancellation.
ck(G(A[0],sum(map(F,A[1]),F()),A[2],F(500000),V0)>0,'bad upper support cannot bracket root')
ck(root(A[0],sum(map(F,A[1]),F()),A[2],volumes[0])!=root(A[0],sum(map(F,A[1]),F()),A[2],volumes[2]),'different V cannot cancel equal states')
result={'status':'passed','checks':checks,'elapsed_s':time.monotonic()-start,'cases':results,'scope':'manufactured analytic EOS and independent exact quadratic roots; no source/native EOS verification','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};Path(__file__).with_name('ORACLE_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
