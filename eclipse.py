import pygame, random, math

pygame.init()
pygame.mixer.quit()

W, H, FPS = 1280, 720, 60
screen = pygame.display.set_mode((W, H), pygame.DOUBLEBUF)
pygame.display.set_caption("Eclipse Vôlei")
clock = pygame.time.Clock()

# ========================= CONFIG =========================
BG=(2,6,23); NAVY=(15,23,42); SLATE=(71,85,105); WHITE=(248,250,252)
BLUE=(37,99,235); BLUE_D=(29,78,216); CYAN=(56,189,248)
RED=(220,38,38); RED_L=(248,113,113); GREEN=(16,185,129)
YELLOW=(251,191,36); ORANGE=(245,158,11); PURPLE=(143,66,255)
GRAY=(148,163,184); PINK=(236,72,153)
SKIN=(254,215,170); SKIN_AI=(252,165,165)
HAIR=(30,27,75); HAIR_AI=(69,26,3)

GRAVITY=.46; COURT_Y=580; LEFT=140; RIGHT=W-140
NET_X=W//2; NET_H=70; NET_TOP=COURT_Y-NET_H; THREE_M=150

TEAM={"left":"ECLIPSE VÔLEI","right":"AURORA VÔLEI"}
DIFFICULTY={
    "FACIL":{"speed":4.7,"reaction":22,"error":.22},
    "NORMAL":{"speed":5.5,"reaction":13,"error":.10},
    "DIFICIL":{"speed":6.15,"reaction":7,"error":.045}
}

CONTROLS={
 "P1":{"left":(pygame.K_a,pygame.K_LEFT),"right":(pygame.K_d,pygame.K_RIGHT),
       "jump":(pygame.K_w,pygame.K_SPACE,pygame.K_UP),"BUMP":(pygame.K_z,),
       "SET":(pygame.K_x,),"SPIKE":(pygame.K_c,),"DROP":(pygame.K_v,),"DIVE":(pygame.K_b,)},
 "P1LOCAL":{"left":(pygame.K_a,),"right":(pygame.K_d),"jump":(pygame.K_w,pygame.K_SPACE),
       "BUMP":(pygame.K_z,),"SET":(pygame.K_x,),"SPIKE":(pygame.K_c,),
       "DROP":(pygame.K_v,),"DIVE":(pygame.K_b,)},
 "P2":{"left":(pygame.K_LEFT,),"right":(pygame.K_RIGHT),"jump":(pygame.K_UP,),
       "BUMP":(pygame.K_j,),"SET":(pygame.K_k,),"SPIKE":(pygame.K_l,),
       "DROP":(pygame.K_o,),"DIVE":(pygame.K_p,)}
}

fonts={}
def font(n,b=True):
    k=(n,b)
    if k not in fonts: fonts[k]=pygame.font.SysFont("arial",n,bold=b)
    return fonts[k]

def txt(s,v,p,n=16,c=WHITE,center=False):
    im=font(n).render(str(v),True,c)
    r=im.get_rect(center=(int(p[0]),int(p[1]))) if center else im.get_rect(topleft=(int(p[0]),int(p[1])))
    s.blit(im,r); return r

def box(s,r,c,rad=12,b=None,w=2):
    pygame.draw.rect(s,c,r,border_radius=rad)
    if b: pygame.draw.rect(s,b,r,width=w,border_radius=rad)

def down(keys,t): return any(k in keys for k in t)

# ========================= EFFECTS =========================
particles=[]; texts=[]; shake=0

class Particle:
    def __init__(self,x,y,vx,vy,c,size,life,shape="circle"):
        self.x=x; self.y=y; self.vx=vx; self.vy=vy
        self.c=c; self.size=size; self.life=life; self.max=life; self.shape=shape
    def update(self,dt):
        q=dt*FPS; self.x+=self.vx*q; self.y+=self.vy*q
        self.vy+=.08*q; self.life-=q
    def draw(self,s):
        if self.life<=0:return
        a=max(0,min(255,int(255*self.life/self.max)))
        lay=pygame.Surface((70,70),pygame.SRCALPHA); col=(*self.c,a)
        if self.shape=="ring":
            r=max(2,int(self.size*(2-self.life/self.max)))
            pygame.draw.circle(lay,col,(35,35),r,3)
        elif self.shape=="spark":
            pygame.draw.line(lay,col,(35-self.size,35),(35+self.size,35),max(2,self.size//2))
        else: pygame.draw.circle(lay,col,(35,35),max(1,int(self.size)))
        s.blit(lay,(int(self.x-35),int(self.y-35)))

def spark(x,y,c=ORANGE,n=10):
    particles.append(Particle(x,y,0,0,c,12,16,"ring"))
    for _ in range(n):
        a=random.random()*math.tau; sp=random.uniform(3,8)
        particles.append(Particle(x,y,math.cos(a)*sp,math.sin(a)*sp,c,random.randint(3,6),random.uniform(16,30),"spark"))

def net_spark():
    for _ in range(10):
        particles.append(Particle(NET_X+random.uniform(-8,8),NET_TOP+random.uniform(0,70),
                                  random.uniform(-2,2),random.uniform(-3,2),WHITE,3,20,"spark"))

class FloatText:
    def __init__(self,x,y,v,c): self.x=x; self.y=y; self.v=v; self.c=c; self.life=45
    def update(self,dt): self.y-=1.5*dt*FPS; self.life-=dt*FPS
    def draw(self,s):
        if self.life<=0:return
        a=max(0,min(255,int(255*self.life/45)))
        lay=pygame.Surface((600,70),pygame.SRCALPHA)
        im=font(27).render(self.v,True,(*self.c,a)); out=font(27).render(self.v,True,(2,6,23,a))
        r=im.get_rect(center=(300,35)); lay.blit(out,(r.x+3,r.y+3)); lay.blit(im,r)
        s.blit(lay,(int(self.x-300),int(self.y-35)))

def say(x,y,v,c=YELLOW): texts.append(FloatText(x,y-20,v,c))

# ========================= BALL =========================
class Ball:
    def __init__(self): self.radius=16; self.reset("left")
    def reset(self,server):
        self.x=LEFT+120 if server=="left" else RIGHT-120; self.y=COURT_Y-170
        self.vx=self.vy=self.spin=0; self.rotation=0; self.cool=0
        self.serving=True; self.last_player=None; self.last_team=None
        self.cross=server; self.touches={"left":0,"right":0}; self.trail=[]; self.timer=0
    def serve(self,team,style="NORMAL",direction=0,charge=.55):
        self.serving=False; self.last_player=None; self.last_team=team
        self.cross=team; self.touches={"left":0,"right":0}
        charge=max(.25,min(1,charge)); direction=max(-1,min(1,direction))
        data={"NORMAL":(9.5,12.7,.45),"FLOAT":(8.8,13,.3),"POWER":(11.8,11.6,.8)}[style]
        bx,vy,spin=data
        bx += {"NORMAL":2.3,"FLOAT":1.8,"POWER":3}[style]*charge
        vy=-(vy+({"NORMAL":.8,"FLOAT":.6,"POWER":1}[style])*charge)
        self.spin=direction*spin
        self.vx=(bx if team=="left" else -bx)+direction*3.4; self.vy=vy; self.cool=10
        say(self.x,self.y,{"NORMAL":"SAQUE","FLOAT":"SAQUE FLUTUANTE","POWER":"SAQUE FORTE"}[style],
            {"NORMAL":YELLOW,"FLOAT":CYAN,"POWER":ORANGE}[style]); spark(self.x,self.y,YELLOW,7)
    def update(self,dt):
        global game_state
        q=dt*FPS
        self.cool=max(0,self.cool-q)
        if self.serving:
            self.timer+=q; self.y=COURT_Y-170+math.sin(pygame.time.get_ticks()*.008)*7; return
        if game_state!="PLAYING": return
        old=self.x
        self.vy+=GRAVITY*(1-min(.14,abs(self.spin)*.018))*q
        self.x+=self.vx*q; self.y+=self.vy*q
        self.vx+=self.spin*.035*q; self.spin*=.992**q; self.vx*=.997**q
        self.rotation+=self.vx*.075*q

        if self.x<LEFT-self.radius-12: spark(LEFT,self.y,WHITE,8); score_point("right"); return
        if self.x>RIGHT+self.radius+12: spark(RIGHT,self.y,WHITE,8); score_point("left"); return
        if abs(self.x-NET_X)<15 and NET_TOP-38<self.y<NET_TOP+2:
            net_spark(); say(self.x,self.y,"ANTENA!",RED_L); score_point("right" if self.x<NET_X else "left"); return

        if (old<NET_X<=self.x or old>NET_X>=self.x):
            if self.y<=NET_TOP+5:
                self.touches={"left":0,"right":0}; self.last_team=None; self.last_player=None
                self.cross="right" if self.x>=NET_X else "left"; say(NET_X,NET_TOP-18,"RECEPCAO",CYAN)
            else:
                net_spark(); self.vx*=.38; self.vy=abs(self.vy)*.42; self.spin*=.4

        if self.x+self.radius>NET_X-7 and self.x-self.radius<NET_X+7 and self.y+self.radius>NET_TOP and self.y-self.radius<COURT_Y:
            net_spark()
            if self.y<NET_TOP+10 and self.vy>0: self.y=NET_TOP-self.radius; self.vy=-abs(self.vy)*.48
            elif self.x<NET_X: self.x=NET_X-8-self.radius; self.vx=-abs(self.vx)*.4; self.vy+=.9
            else: self.x=NET_X+8+self.radius; self.vx=abs(self.vx)*.4; self.vy+=.9

        if self.y+self.radius>=COURT_Y:
            self.y=COURT_Y-self.radius; spark(self.x,COURT_Y-5,YELLOW,10)
            score_point("right" if self.x<NET_X else "left"); return

        sp=math.hypot(self.vx,self.vy)
        if sp>2.2:
            self.trail.append((self.x,self.y,sp)); self.trail=self.trail[-10:]
        elif self.trail:self.trail.pop(0)
    def draw(self,s):
        for i,(x,y,sp) in enumerate(self.trail):
            p=(i+1)/len(self.trail); size=max(2,int(self.radius*(.3+.45*p)))
            lay=pygame.Surface((size*4,size*4),pygame.SRCALPHA)
            pygame.draw.circle(lay,(* (RED_L if sp>13 else YELLOW),int(p*60)),(size*2,size*2),size)
            s.blit(lay,(int(x-size*2),int(y-size*2)))
        sh=max(.15,1-max(0,COURT_Y-self.y)/500)
        pygame.draw.ellipse(s,BG,(int(self.x-self.radius*sh),COURT_Y+5-int(self.radius*.3*sh),
                                   int(self.radius*2*sh),int(self.radius*.6*sh)))
        x,y=int(self.x),int(self.y)
        pygame.draw.circle(s,(203,213,225),(x,y),17); pygame.draw.circle(s,WHITE,(x-2,y-2),16)
        r=(x-14,y-14,28,28)
        pygame.draw.arc(s,BLUE,r,self.rotation-.2,self.rotation+1.5,4)
        pygame.draw.arc(s,ORANGE,r,self.rotation+1.8,self.rotation+3.7,4)
        pygame.draw.arc(s,BLUE_D,r,self.rotation+4,self.rotation+5.7,4)
        pygame.draw.circle(s,NAVY,(x,y),16,1); pygame.draw.circle(s,WHITE,(x-6,y-6),5)

ball=Ball()

# ========================= PLAYERS =========================
class Player:
    def __init__(self,x,team,human=False,num="7",name="Jogador"):
        self.team=team; self.human=human; self.ai=not human; self.num=num; self.name=name
        self.skin=SKIN if team=="left" else SKIN_AI; self.jersey=BLUE if team=="left" else RED
        self.accent=BLUE_D if team=="left" else (153,27,27); self.hair=HAIR if team=="left" else HAIR_AI
        self.x=x; self.y=COURT_Y; self.reset(x); self.zone=0
    def reset(self,x=None):
        if x is not None:self.x=x
        self.y=COURT_Y; self.vx=self.vy=0; self.move=0; self.state="IDLE"
        self.timer=0; self.progress=0; self.grounded=True; self.stamina=100
        self.ai_timer=random.uniform(0,12); self.anim=random.random()*10
    def jump(self,force=14.5):
        if self.grounded and self.stamina>=10:
            self.vy=-force; self.grounded=False; self.stamina-=10; self.state="IDLE"
    def side_ok(self,x): return x<NET_X+16 if self.team=="left" else x>NET_X-16
    def can_act(self): return self.state=="IDLE" and ball.cool<=0 and game_state=="PLAYING" and (not self.ai or self.ai_timer<=0)
    def action(self,a):
        if not self.can_act(): return False
        if ball.serving:
            if self.team!=server:return False
            ball.serve(self.team,{"SPIKE":"POWER","SET":"FLOAT"}.get(a,"NORMAL"),serve_dir,serve_charge)
            self.ai_timer=DIFFICULTY[difficulty]["reaction"]; return True
        self.state=a; self.timer=22; self.progress=0; return self.hit()
    def hit(self):
        global shake
        if ball.serving or ball.cool>0 or game_state!="PLAYING": return False
        face=1 if self.team=="left" else -1
        if self.state=="DIVE":
            ok=self.grounded and ball.y>COURT_Y-105 and math.hypot(ball.x-(self.x+face*28),ball.y-(self.y-25))<145
            if not ok:return False
            ball.touches[self.team]+=1; ball.last_team=self.team; ball.last_player=self; ball.cool=13
            target=teammate(self); tx=target.x if target else NET_X-face*85
            ball.vx=max(-7,min(7,(tx-ball.x)*.1)); ball.vy=-10.8; self.vy=-4.5
            say(ball.x,ball.y,f"MERGULHO #{ball.touches[self.team]}",GREEN); spark(ball.x,ball.y,GREEN,14); return True

        reach={"BUMP":(22,45,105),"SET":(3,82,102)}.get(self.state,(28,83,120))
        hx,hy,r=self.x+face*reach[0],self.y-reach[1],reach[2]
        if math.hypot(ball.x-hx,ball.y-hy)>r:return False
        if mode=="2V2_BOT" and ball.last_player is self:
            say(ball.x,ball.y,"TOQUE DUPLO!",RED_L); score_point("right" if self.team=="left" else "left"); return False
        n=ball.touches[self.team]
        if n>=3:
            say(ball.x,ball.y,"4 TOQUES!",RED_L); score_point("right" if self.team=="left" else "left"); return False
        if self.ai and random.random()<DIFFICULTY[difficulty]["error"]:
            self.ai_timer=DIFFICULTY[difficulty]["reaction"]+8; say(self.x,self.y-100,"ERRO",RED_L); return False

        ball.touches[self.team]+=1; ball.last_team=self.team; ball.last_player=self; ball.cool=12; n+=1
        target=teammate(self); tx=target.x if target else NET_X+face*80

        if self.state=="BUMP":
            if n==3: tx=NET_X+face*35; ball.vy=-11.8
            else: ball.vy=-14.6; ball.spin=(tx-ball.x)*.008
            ball.vx=max(-6.5,min(6.5,(tx+face*random.uniform(-20,20)-ball.x)*.09))
            say(ball.x,ball.y,f"MANCHETE #{n}",GREEN); spark(ball.x,ball.y,GREEN,10)
        elif self.state=="SET":
            if n==3: tx=NET_X+face*95; ball.vy=-11.2
            else: ball.vy=-17.4
            ball.vx=max(-6,min(6,(tx-ball.x)*.095)); ball.spin=face*.18
            say(ball.x,ball.y,f"TOQUE #{n}",CYAN); spark(ball.x,ball.y,CYAN,10)
        elif self.state=="DROP":
            tx=NET_X+face*135; ball.vx=max(-5.8,min(5.8,(tx-ball.x)*.075)); ball.vy=-8; ball.spin=face*.25
            say(ball.x,ball.y,f"LARGADINHA #{n}",CYAN); spark(ball.x,ball.y,CYAN,12)
        else:
            power=13.4+random.random()*2.8 if not self.grounded else 10.7+random.random()*2.6
            ball.vx=face*power; ball.vy=(4.4+random.random()*4.4) if not self.grounded else -5
            ball.spin=face*(.95 if not self.grounded else .7)
            say(ball.x,ball.y,f"CORTADA #{n}",RED_L if n==3 else ORANGE); spark(ball.x,ball.y,RED_L if n==3 else ORANGE,16)
            shake=max(shake,12 if n==3 else 7)
        return True
    def ai_update(self):
        if not self.ai or game_state!="PLAYING":return
        info=DIFFICULTY[difficulty]; own=[p for p in players if p.team==self.team]
        incoming=self.side_ok(ball.x) and not ball.serving; touches=ball.touches[self.team]
        if len(own)>1:
            base=(LEFT+(115 if self.zone==0 else 265)) if self.team=="left" else (RIGHT-(115 if self.zone==0 else 265))
        else: base=LEFT+190 if self.team=="left" else RIGHT-190
        projected=max(LEFT+40,min(RIGHT-40,ball.x+ball.vx*8))
        target=base
        if incoming:
            candidate=min(own,key=lambda p:abs(p.x-projected))
            if touches==0: target=projected+(12 if self.team=="left" else -12) if self is candidate else base+(projected-base)*.12
            elif touches==1:
                setter=min(own,key=lambda p:abs((NET_X-(120 if self.team=="left" else -120))-p.x))
                target=NET_X-(118 if self.team=="left" else -118) if self is setter else projected+(18 if self.team=="left" else -18)
            else: target=NET_X-(70 if self.team=="left" else -70)
        else: target=base+(projected-base)*(.18 if len(own)>1 else .32)
        target=max(LEFT+30,min(RIGHT-30,target))
        target=min(target,NET_X-42) if self.team=="left" else max(target,NET_X+42)
        dx=target-self.x; self.move=math.copysign(1,dx) if abs(dx)>7 else 0
        if not incoming:return
        reach=math.hypot(ball.x-self.x,ball.y-(self.y-58))
        if reach<145 and ball.y>COURT_Y-235:
            if self.grounded and ball.y>COURT_Y-105 and reach<138 and random.random()<.28:self.action("DIVE")
            elif not self.grounded and abs(ball.x-NET_X)<120 and ball.y<NET_TOP+95:self.action(random.choice(["SPIKE","SPIKE","DROP","SET"]))
            elif ball.y<COURT_Y-115 and random.random()<.34:
                a=random.choice(["BUMP","SET","SPIKE","DROP"])
                if a=="SPIKE" and self.grounded:self.jump()
                if self.grounded or a!="SPIKE":self.action(a)
            else:self.action(random.choice(["BUMP","BUMP","SET","DROP"]))
            self.ai_timer=info["reaction"]+random.uniform(2,9)
    def update(self,dt):
        q=dt*FPS
        stamina=.72 if self.stamina<20 else .88 if self.stamina<40 else 1
        maxsp=(6.65 if self.human else DIFFICULTY[difficulty]["speed"]+.45)*stamina
        desired=self.move*maxsp; accel=.92 if self.grounded else .52
        self.vx+=max(-accel*q,min(accel*q,desired-self.vx))
        if abs(self.move)<.05:self.vx*=.80**q
        self.vy+=GRAVITY*q; self.x+=self.vx*q; self.y+=self.vy*q
        if self.y>=COURT_Y:self.y=COURT_Y; self.vy=0; self.grounded=True
        else:self.grounded=False
        self.x=max(LEFT+24,min(NET_X-30,self.x)) if self.team=="left" else max(NET_X+30,min(RIGHT-24,self.x))
        if self.timer>0:
            self.timer-=q; self.progress=max(0,min(1,1-self.timer/26))
            if self.timer<=0:self.state="IDLE"; self.progress=0
        self.ai_timer=max(0,self.ai_timer-q)
        self.stamina=max(0,min(100,self.stamina-(.11*abs(self.move)*q) if abs(self.move)>.05 else self.stamina+.3*q))
        self.anim+=abs(self.vx)*.026*q+.023*q
        self.ai_update()
        if self.state!="IDLE" and self.timer>0 and ball.cool<=0:self.hit()
    def draw(self,s):
        face=1 if self.team=="left" else -1; moving=abs(self.vx)>.45
        ph=math.sin(self.anim) if moving else 0; ph2=math.sin(self.anim+math.pi) if moving else 0
        crouch=9*math.sin(math.pi*self.progress) if self.state=="BUMP" else 0
        bx=self.x+max(-7,min(7,self.vx*.7)); by=self.y-crouch; hip=by-37
        jump=max(0,COURT_Y-self.y)
        pygame.draw.ellipse(s,BG,(int(self.x-max(18,44-jump*.1)/2),COURT_Y-3,int(max(18,44-jump*.1)),int(max(5,12-jump*.035))))
        if self.state=="SPIKE" and not self.grounded:
            kl=(bx-15,hip+13); kr=(bx+15,hip+8); fl=(bx-25,hip+31); fr=(bx+25,hip+27)
        else:
            a=ph*9 if moving else 0; b=ph2*9 if moving else 0
            kl=(bx-8+a,hip+20); kr=(bx+8+b,hip+20); fl=(bx-11+b,self.y-5); fr=(bx+11+a,self.y-5)
        for sh,k,f in [((bx-7,hip),kl,fl),((bx+7,hip),kr,fr)]:
            pygame.draw.line(s,self.skin,sh,k,8); pygame.draw.circle(s,self.skin,(int(k[0]),int(k[1])),5)
            pygame.draw.line(s,self.skin,k,f,8); pygame.draw.circle(s,NAVY,(int(k[0]),int(k[1])),6,2)
        pygame.draw.ellipse(s,WHITE,(int(fl[0]-9),int(fl[1]-4),19,9)); pygame.draw.ellipse(s,WHITE,(int(fr[0]-9),int(fr[1]-4),19,9))
        torso=pygame.Rect(int(bx-15),int(by-68),30,34); box(s,torso,self.jersey,7)
        pygame.draw.rect(s,self.accent,(torso.x if face>0 else torso.right-5,torso.y,5,torso.height)); txt(s,self.num,torso.center,12,center=True)
        pygame.draw.rect(s,self.skin,(int(bx-5),int(by-72),10,12)); hx,hy=bx,by-86
        pygame.draw.circle(s,self.skin,(int(hx),int(hy)),14); pygame.draw.circle(s,self.hair,(int(hx),int(hy-4)),14)
        pygame.draw.arc(s,self.hair,(int(hx-14),int(hy-13),28,25),math.pi,math.tau,5)
        pygame.draw.circle(s,NAVY,(int(hx+face*5),int(hy-2)),2)
        sl=(bx-11,by-61); sr=(bx+11,by-61)
        if self.state=="BUMP":
            ay=by-45; hand=bx+face*25
            pygame.draw.line(s,self.skin,sl,(bx+face*5,ay),7); pygame.draw.line(s,self.skin,sr,(bx+face*10,ay+2),7)
            pygame.draw.line(s,self.skin,(bx+face*5,ay),(hand,ay+3),7); pygame.draw.line(s,self.skin,(bx+face*10,ay+2),(hand+face*3,ay+3),7)
        elif self.state=="SET":
            for z in(-1,1):
                sh=sl if z<0 else sr; hand=(bx+z*13+face*7,by-99)
                pygame.draw.line(s,self.skin,sh,(bx+z*11,by-82),7); pygame.draw.line(s,self.skin,(bx+z*11,by-82),hand,7)
                pygame.draw.circle(s,self.skin,(int(hand[0]),int(hand[1])),5)
        elif self.state=="SPIKE":
            d=(bx+face*6,by-103); o=(bx-face,by-88)
            pygame.draw.line(s,self.skin,sl,(bx-face*4,by-80),7); pygame.draw.line(s,self.skin,(bx-face*4,by-80),o,7)
            pygame.draw.line(s,self.skin,sr,(bx+face*2,by-83),7); pygame.draw.line(s,self.skin,(bx+face*2,by-83),d,7)
            pygame.draw.circle(s,self.skin,(int(d[0]),int(d[1])),5)
        else:
            pygame.draw.line(s,self.skin,sl,(bx-18,by-35+ph2*5),7); pygame.draw.line(s,self.skin,sr,(bx+18,by-35-ph2*5),7)
        pygame.draw.rect(s,(30,41,59),(int(kl[0]-4),int(kl[1]-2),8,6),border_radius=2)
        pygame.draw.rect(s,(30,41,59),(int(kr[0]-4),int(kr[1]-2),8,6),border_radius=2)
        txt(s,self.name,(self.x,self.y+17),10,center=True)
        if self.state!="IDLE": pygame.draw.circle(s,{"BUMP":GREEN,"SET":CYAN,"SPIKE":RED_L,"DROP":CYAN,"DIVE":GREEN}.get(self.state,WHITE),(int(self.x),int(self.y-119)),5)

players=[]; left_team=[]; right_team=[]

def teammate(p):
    a=[x for x in players if x.team==p.team and x is not p]
    return min(a,key=lambda x:abs(x.x-ball.x)) if a else None

def start_x(team,n,i):
    if n==1:return LEFT+175 if team=="left" else RIGHT-175
    return (LEFT+115+i*150) if team=="left" else (RIGHT-115-i*150)

def configure(m):
    global mode,players,left_team,right_team
    mode=m
    if m=="1V1_BOT":
        left_team=[Player(start_x("left",1,0),"left",True,"7","VOCE")]
        right_team=[Player(start_x("right",1,0),"right",False,"1","AURORA 1")]
    elif m=="2V2_BOT":
        left_team=[Player(start_x("left",2,0),"left",True,"7","VOCE"),Player(start_x("left",2,1),"left",False,"11","ALIADA")]
        right_team=[Player(start_x("right",2,0),"right",False,"1","AURORA 1"),Player(start_x("right",2,1),"right",False,"2","AURORA 2")]
    else:
        left_team=[Player(start_x("left",1,0),"left",True,"7","P1")]
        right_team=[Player(start_x("right",1,0),"right",True,"10","P2")]
    for t in(left_team,right_team):
        for i,p in enumerate(t):p.zone=i
    players=left_team+right_team

def human(side): return next((p for p in (left_team if side=="left" else right_team) if p.human),None)

# ========================= MATCH STATE =========================
game_state="MENU"; menu="MAIN"; mode=None; pending=None; difficulty="NORMAL"
score={"left":0,"right":0}; sets={"left":0,"right":0}; last_score={"left":0,"right":0}
server="left"; point_timer=0; point_msg=""; set_msg=""
serve_style="NORMAL"; serve_dir=0; serve_charge=.55; charge_dir=1
keys=set()

def target_points(): return 15 if sum(sets.values())>=2 else 25

def reset_match():
    global score,sets,last_score,server,point_timer,point_msg,set_msg,game_state,serve_style,serve_dir,serve_charge,charge_dir
    score={"left":0,"right":0}; sets={"left":0,"right":0}; last_score={"left":0,"right":0}
    server="left"; point_timer=0; point_msg=""; set_msg=""; serve_style="NORMAL"; serve_dir=0; serve_charge=.55; charge_dir=1
    for team,side in((left_team,"left"),(right_team,"right")):
        for i,p in enumerate(team):p.reset(start_x(side,len(team),i))
    ball.reset(server); game_state="PLAYING"

def start(m): configure(m); reset_match()

def score_point(w):
    global server,point_timer,point_msg,game_state,sets,score,last_score,set_msg
    if game_state!="PLAYING":return
    score[w]+=1
    if mode=="2V2_BOT" and w!=server:
        t=left_team if w=="left" else right_team
        if len(t)>1:t[:]=[t[1],t[0]]; [setattr(p,"zone",i) for i,p in enumerate(t)]
        say(NET_X,205,"RODIZIO!",PURPLE)
    server=w; point_msg="PONTO DO SEU TIME!" if w=="left" else "PONTO DO ADVERSARIO!"; point_timer=75
    other="right" if w=="left" else "left"
    if score[w]>=target_points() and score[w]-score[other]>=2:
        sets[w]+=1; last_score=score.copy(); score={"left":0,"right":0}
        set_msg=f"{TEAM[w]} GANHOU O SET!"; game_state="MATCHOVER" if sets[w]>=2 else "SET_WON"
    else: game_state="POINT_SCORED"

def continue_game():
    global game_state
    ball.reset(server)
    for team,side in((left_team,"left"),(right_team,"right")):
        for i,p in enumerate(team):p.reset(start_x(side,len(team),i))
    game_state="PLAYING"

# ========================= DRAW =========================
def court(s):
    s.fill(BG)
    for y in range(COURT_Y):
        t=y/COURT_Y; pygame.draw.line(s,(int(2+12*t),int(6+14*t),int(23+31*t)),(0,y),(W,y))
    for x in(110,360,610,860,1110):
        pygame.draw.rect(s,(34,48,72),(x,76,150,6),border_radius=3)
        pygame.draw.rect(s,(70,92,126),(x+35,80,80,3),border_radius=2)
    seats=[(30,41,59),(38,50,72),(45,58,82)]
    for row,y in enumerate((315,338,361)):
        pygame.draw.rect(s,seats[row],(0,y,W,22))
        for x in range(18,W-18,31):
            b=math.sin(x*.065+row)*2; skin=(226,190,160) if (x//31+row)%3 else (245,205,173)
            shirt=(76,89,115) if (x//31+row)%2 else (108,55,142)
            pygame.draw.circle(s,skin,(x,int(y-5+b)),6); pygame.draw.rect(s,shirt,(x-8,int(y+5+b),16,13),border_radius=5)
    box(s,(LEFT,COURT_Y-118,RIGHT-LEFT,118),(10,130,154),0)
    pygame.draw.rect(s,(15,142,167),(LEFT+7,COURT_Y-111,RIGHT-LEFT-14,104))
    for x in range(LEFT+22,RIGHT-20,115):pygame.draw.line(s,(19,114,133),(x,COURT_Y+9),(x+28,H),3)
    for a,b in [((LEFT,COURT_Y),(RIGHT,COURT_Y),7),((LEFT,COURT_Y-118),(RIGHT,COURT_Y-118),5),
                ((LEFT,COURT_Y-118),(LEFT,COURT_Y),5),((RIGHT,COURT_Y-118),(RIGHT,COURT_Y),5)]:
        pygame.draw.line(s,WHITE,a,b if isinstance(b,int) else b,b)
    pygame.draw.line(s,(38,73,151),(NET_X-THREE_M,COURT_Y),(NET_X-THREE_M,COURT_Y-118),5)
    pygame.draw.line(s,(38,73,151),(NET_X+THREE_M,COURT_Y),(NET_X+THREE_M,COURT_Y-118),5)
    pygame.draw.line(s,(208,242,255),(NET_X,COURT_Y-118),(NET_X,COURT_Y),2)
    box(s,(56,260,260,42),NAVY,10,PURPLE); txt(s,TEAM["left"],(186,281),15,center=True)
    box(s,(964,260,260,42),NAVY,10,ORANGE); txt(s,TEAM["right"],(1094,281),15,center=True)
    pygame.draw.rect(s,(148,163,184),(NET_X-6,NET_TOP-3,12,NET_H+7))
    pygame.draw.line(s,WHITE,(NET_X-10,NET_TOP+2),(NET_X+10,NET_TOP+2),5)
    pygame.draw.line(s,(123,141,163),(NET_X,NET_TOP+7),(NET_X,COURT_Y),2)
    pygame.draw.line(s,WHITE,(NET_X-2,NET_TOP-38),(NET_X-2,NET_TOP+2),4)
    pygame.draw.circle(s,ORANGE,(NET_X-2,NET_TOP-41),5)

def hud(s):
    box(s,(W//2-250,16,500,84),NAVY,18,SLATE)
    txt(s,TEAM["left"],(W//2-145,31),11,CYAN,True); txt(s,TEAM["right"],(W//2+145,31),11,RED_L,True)
    txt(s,score["left"],(W//2-72,69),34,CYAN,True); txt(s,score["right"],(W//2+72,69),34,RED_L,True); txt(s,":",(W//2,66),24,SLATE,True)
    txt(s,f"SET {sum(sets.values())+1} | PRIMEIRO A {target_points()} | SETS {sets['left']}-{sets['right']}",(W//2,112),14,WHITE,True)
    box(s,(34,36,245,84),NAVY,12,BLUE_D); txt(s,f"ESQUERDA: {ball.touches['left']}/3",(50,50),14,CYAN); txt(s,f"DIREITA: {ball.touches['right']}/3",(50,80),14,RED_L)
    txt(s,f"{difficulty} | {mode_label(mode)}",(W-245,55),12,GRAY)
    p=human("left")
    if p:
        box(s,(40,H-51,180,14),NAVY,7); box(s,(42,H-49,max(2,int(176*p.stamina/100)),10),CYAN,5); txt(s,"STAMINA",(46,H-72),10)

def mode_label(m):return {"1V1_BOT":"1V1 x BOT","2V2_BOT":"2V2 x BOTS","1V1_LOCAL":"1V1 LOCAL"}.get(m,"-")

def serve_panel(s):
    if not ball.serving or game_state!="PLAYING" or not human(server):return
    box(s,(330,H-116,620,88),NAVY,18,ORANGE,2); txt(s,"SAQUE",(392,H-96),16,ORANGE,True)
    for i,(name,sty,c) in enumerate([("NORMAL","NORMAL",GREEN),("FLUTUANTE","FLOAT",CYAN),("FORTE","POWER",RED_L)]):
        x=455+i*130; sel=serve_style==sty; box(s,(x,H-107,116,30),c if sel:(35,45,62),10,c,2); txt(s,name,(x+58,H-92),10,center=True)
    box(s,(455,H-64,315,12),(30,41,59),6,SLATE,1); box(s,(457,H-62,max(4,int(311*serve_charge)),8),ORANGE,4)
    d="ESQUERDA" if serve_dir<-.25 else "DIREITA" if serve_dir>.25 else "CENTRO"
    txt(s,f"DIRECAO: {d}",(820,H-92),11,WHITE,True); txt(s,"Z normal | X flutuante | C forte | A/D = direcao | ESPACO = sacar",(640,H-38),10,GRAY,True)

def overlay(s,title,sub=""):
    o=pygame.Surface((W,H),pygame.SRCALPHA); o.fill((2,6,23,190)); s.blit(o,(0,0))
    box(s,(285,100,710,500),NAVY,28,SLATE); txt(s,title,(640,185),40,ORANGE,True)
    if sub:txt(s,sub,(640,230),16,WHITE,True)

def menu_main(s):
    court(s); overlay(s,"ECLIPSE VÔLEI","JOGO DE VÔLEI EM PYTHON")
    for r,t in [((420,320,440,58),"JOGAR"),((420,395,440,58),"COMO JOGAR"),((420,470,440,58),"SAIR")]:
        box(s,r,PURPLE if t=="JOGAR" else NAVY,16,SLATE); txt(s,t,(640,r[1]+29),20,WHITE,True)

def menu_mode(s):
    court(s); overlay(s,"ESCOLHA O MODO","Clique em uma opção")
    for r,t,sub,c in [((180,270,270,180),"1V1 BOT","Voce x bot",BLUE),((505,270,270,180),"2V2 BOTS","Voce + aliada x 2 bots",PURPLE),((830,270,270,180),"1V1 LOCAL","P1 x P2",PINK)]:
        box(s,r,(30,41,59),20,c,3); txt(s,t,(r[0]+r[2]/2,r[1]+55),27,c,True); txt(s,sub,(r[0]+r[2]/2,r[1]+105),14,WHITE,True); txt(s,"CLIQUE",(r[0]+r[2]/2,r[1]+145),11,GRAY,True)

def menu_diff(s):
    court(s); overlay(s,"ESCOLHA A DIFICULDADE", "Modo: "+mode_label(pending))
    for r,t,c in [((315,270,200,170),"FACIL",GREEN),((540,270,200,170),"NORMAL",CYAN),((765,270,200,170),"DIFICIL",RED_L)]:
        box(s,r,(30,41,59),18,c,3); txt(s,t,(r[0]+100,r[1]+60),25,c,True); txt(s,"CLIQUE",(r[0]+100,r[1]+115),11,GRAY,True)

def tutorial(s):
    court(s); overlay(s,"COMO JOGAR")
    rows=[("MOVER","P1 A/D | P2 SETAS"),("PULAR","P1 W/ESPACO | P2 ↑"),("MANCHETE","P1 Z | P2 J"),
          ("TOQUE","P1 X | P2 K"),("CORTADA","P1 C | P2 L"),("LARGADINHA","P1 V | P2 O"),("MERGULHO","P1 B | P2 P")]
    y=285
    for a,b in rows:box(s,(350,y,580,38),(30,41,59),8,SLATE);txt(s,a,(470,y+19),13,CYAN,True);txt(s,b,(720,y+19),13,WHITE,True);y+=45
    txt(s,"3 toques por equipe | no 2V2 não pode tocar duas vezes seguidas",(640,620),13,YELLOW,True)

def pause(s):
    overlay(s,"PAUSADO"); txt(s,"ENTER = continuar | R = reiniciar | ESC = menu",(640,300),17,WHITE,True)

def matchover(s):
    overlay(s,"PARTIDA ENCERRADA",TEAM["left"] if sets["left"]>sets["right"] else TEAM["right"])
    txt(s,f"SETS {sets['left']} - {sets['right']}",(640,340),36,WHITE,True)
    txt(s,f"ULTIMO SET {last_score['left']} - {last_score['right']}",(640,385),18,GRAY,True)
    txt(s,"ENTER = jogar novamente | ESC = menu",(640,480),16,WHITE,True)

# ========================= INPUT =========================
def update_move():
    for side,keyname in [("left","P1"),("right","P2")]:
        p=human(side)
        if not p:continue
        c=CONTROLS["P1LOCAL" if mode=="1V1_LOCAL" and side=="left" else keyname]
        d=(-1 if down(keys,c["left"]) else 0)+(1 if down(keys,c["right"]) else 0)
        p.move=d

def serve_direction():
    global serve_dir
    p=human(server)
    if not p:return
    c=CONTROLS["P1LOCAL" if p is human("left") and mode=="1V1_LOCAL" else "P1" if p is human("left") else "P2"]
    serve_dir=(-1 if down(keys,c["left"]) else 0)+(1 if down(keys,c["right"]) else 0)

def human_action(p,a):
    if p is None:return
    p.action(a)

# ========================= LOOP =========================
running=True
while running:
    dt=min(clock.tick(FPS)/1000,.033)
    for e in pygame.event.get():
        if e.type==pygame.QUIT:running=False
        elif e.type==pygame.KEYDOWN:
            keys.add(e.key)
            if e.key==pygame.K_ESCAPE:
                if game_state=="PLAYING":game_state="PAUSED"
                elif game_state=="PAUSED":game_state="MENU";menu="MAIN";keys.clear()
                elif game_state=="MENU" and menu!="MAIN":menu="MAIN"
                elif game_state=="MATCHOVER":game_state="MENU";menu="MAIN"
                else:running=False
            elif e.key==pygame.K_RETURN:
                if game_state=="MENU":
                    if menu=="MAIN":menu="MODE"
                    elif menu=="MODE":pending="1V1_BOT";menu="DIFF"
                    elif menu=="DIFF":difficulty="NORMAL";start(pending)
                    else:menu="MAIN"
                elif game_state=="PAUSED":game_state="PLAYING"
                elif game_state=="SET_WON":continue_game()
                elif game_state=="MATCHOVER":reset_match()
            elif game_state=="PAUSED" and e.key==pygame.K_r:reset_match()

            if game_state=="PLAYING":
                for side in ("left","right"):
                    p=human(side)
                    if not p:continue
                    c=CONTROLS["P1LOCAL" if mode=="1V1_LOCAL" and side=="left" else "P1" if side=="left" else "P2"]
                    if e.key in c["jump"]:
                        if ball.serving and server==side:p.action("BUMP")
                        else:p.jump()
                    for a in ("BUMP","SET","SPIKE","DROP","DIVE"):
                        if e.key in c[a]:
                            if ball.serving and server==side:
                                if a=="BUMP":p.action("BUMP")
                                elif a=="SET":p.action("SET")
                                elif a=="SPIKE":p.action("SPIKE")
                            elif not ball.serving:
                                if a=="SPIKE":p.jump()
                                p.action(a)
        elif e.type==pygame.KEYUP:keys.discard(e.key)
        elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
            x,y=e.pos
            if game_state=="MENU":
                if menu=="MAIN":
                    if 420<=x<=860 and 320<=y<=378:menu="MODE"
                    elif 420<=x<=860 and 395<=y<=453:menu="TUTORIAL"
                    elif 420<=x<=860 and 470<=y<=528:running=False
                elif menu=="MODE":
                    if 180<=x<=450 and 270<=y<=450:pending="1V1_BOT";menu="DIFF"
                    elif 505<=x<=775 and 270<=y<=450:pending="2V2_BOT";menu="DIFF"
                    elif 830<=x<=1100 and 270<=y<=450:start("1V1_LOCAL")
                elif menu=="DIFF":
                    if 315<=x<=515 and 270<=y<=440:difficulty="FACIL";start(pending)
                    elif 540<=x<=740 and 270<=y<=440:difficulty="NORMAL";start(pending)
                    elif 765<=x<=965 and 270<=y<=440:difficulty="DIFICIL";start(pending)
            elif game_state=="PAUSED" and 430<=x<=850 and 250<=y<=350:game_state="PLAYING"
            elif game_state=="MATCHOVER":
                if 450<=x<=830 and 430<=y<=510:reset_match()
                else:game_state="MENU";menu="MAIN"

    if game_state=="PLAYING":
        if ball.serving:
            serve_charge+=charge_dir*.018*(dt*FPS)
            if serve_charge>=1:serve_charge=1;charge_dir=-1
            if serve_charge<=.28:serve_charge=.28;charge_dir=1
            serve_direction()
            if server=="right" and mode!="1V1_LOCAL" and ball.timer>34:
                sty="POWER" if difficulty=="DIFICIL" and random.random()<.42 else "FLOAT" if random.random()<.3 else "NORMAL"
                ball.serve("right",sty,random.uniform(-.75,.75),random.uniform(.45,1))
        update_move()
        ball.update(dt)
        for p in players:p.update(dt)
    elif game_state=="POINT_SCORED":
        point_timer-=dt*FPS
        if point_timer<=0:continue_game()

    for p in particles[:]:
        p.update(dt)
        if p.life<=0:particles.remove(p)
    for t in texts[:]:
        t.update(dt)
        if t.life<=0:texts.remove(t)

    frame=pygame.Surface((W,H)).convert()
    if game_state=="MENU":
        {"MAIN":menu_main,"MODE":menu_mode,"DIFF":menu_diff,"TUTORIAL":tutorial}[menu](frame)
    else:
        court(frame)
        for p in players:p.draw(frame)
        ball.draw(frame)
        for p in particles:p.draw(frame)
        for t in texts:t.draw(frame)
        hud(frame);serve_panel(frame)
        if game_state=="POINT_SCORED":txt(frame,point_msg,(W//2,H//2-80),38,YELLOW,True)
        elif game_state=="SET_WON":txt(frame,set_msg,(W//2,H//2-80),30,YELLOW,True);txt(frame,"ENTER para continuar",(W//2,H//2-35),16,WHITE,True)
        elif game_state=="PAUSED":pause(frame)
        elif game_state=="MATCHOVER":matchover(frame)

    if shake>0:
        screen.fill(BG);screen.blit(frame,(random.randint(-int(shake),int(shake)),random.randint(-int(shake),int(shake))))
        shake*=.85**(dt*FPS)
        if shake<.5:shake=0
    else:screen.blit(frame,(0,0))
    pygame.display.flip()

pygame.quit()
