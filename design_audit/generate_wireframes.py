from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
OUT=Path('design_audit'); OUT.mkdir(exist_ok=True)
W,H=1600,1000
bg='#F4F7FB'; panel='#FFFFFF'; ink='#172338'; muted='#68768B'; line='#E0E7F0'; blue='#2457D6'; blue2='#EAF0FF'; green='#168567'; red='#C44852'; amber='#B77A12'; navy='#14233B'
try:
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',16); bold=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',16); small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',13); big=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',25)
except: font=bold=small=big=ImageFont.load_default()
def rr(d,box,fill,outline=None,r=12,w=1): d.rounded_rectangle(box,radius=r,fill=fill,outline=outline,width=w)
def text(d,xy,s,f=font,fill=ink): d.text(xy,s,font=f,fill=fill)
def base(title,active):
 im=Image.new('RGB',(W,H),bg); d=ImageDraw.Draw(im)
 d.rectangle((0,0,248,H),fill=navy)
 text(d,(26,24),'Vprofitables',big,'#FFFFFF'); text(d,(26,62),'INVESTMENT WORKSPACE',small,'#A9B8CD')
 for i,(label,ico) in enumerate([('Overview','⌂'),('Portfolio','▦'),('Research','⌕'),('Markets','↗'),('Analytics','▥'),('Settings','⚙')]):
  y=128+i*52
  if label==active: rr(d,(14,y-6,232,y+38),'#263C62',None,9)
  text(d,(28,y),ico,font,'#FFFFFF' if label==active else '#9EADC2'); text(d,(58,y),label,font,'#FFFFFF' if label==active else '#B8C5D6')
 d.line((0,455,248,455),fill='#354762'); text(d,(26,478),'WORKSPACE',small,'#93A5BC'); text(d,(26,515),'Primary portfolio',font,'#FFFFFF'); text(d,(26,544),'NSE · Paper trading',small,'#A9B8CD')
 d.rectangle((248,0,W,70),fill=panel); text(d,(280,23),title,big); rr(d,(1260,17,1450,53),'#F3F6FA',line,8); text(d,(1277,27),'As of 27 Oct 2026',small,muted); rr(d,(1470,16,1538,54),blue,None,9); text(d,(1490,27),'AB',small,'#FFFFFF')
 return im,d
def card(d,x,y,w,h,title,sub=None):
 rr(d,(x,y,x+w,y+h),panel,line,12); text(d,(x+20,y+16),title,bold); 
 if sub: text(d,(x+20,y+42),sub,small,muted)
def metric(d,x,y,w,label,val,change,color=ink):
 card(d,x,y,w,112,label); text(d,(x+20,y+49),val,big); text(d,(x+20,y+82),change,small,color)
# overview
im,d=base('Market overview','Overview')
text(d,(280,96),'Tuesday, 27 October 2026  ·  Market session: Closed',small,muted)
rr(d,(1270,87,1538,123),panel,line,8); text(d,(1290,97),'Search symbol or action  ⌕',small,muted)
metric(d,280,140,285,'Portfolio value','₹12,48,620','+₹18,420  ·  +1.50%',green)
metric(d,583,140,285,'Unrealized P&L','+₹26,840','Today +₹3,210',green)
metric(d,886,140,285,'NIFTY 50','24,318.60','+0.42%  ·  delayed/EOD',green)
metric(d,1189,140,349,'Risk status','Moderate','VaR 95% · ₹42,600',amber)
card(d,280,270,820,350,'Market pulse','Index breadth · sectors · session status')
# chart schematic
rr(d,(304,333,1076,565),'#FBFCFE',line,8)
for i in range(5): d.line((320,365+i*43,1060,365+i*43),fill='#E9EEF5')
pts=[(325,518),(390,490),(455,510),(520,445),(585,465),(650,419),(715,440),(780,384),(845,405),(910,370),(975,390),(1045,345)]
d.line(pts,fill=blue,width=4,joint='curve')
text(d,(320,580),'09:15',small,muted);text(d,(1000,580),'15:30',small,muted)
card(d,1120,270,418,350,'Your positions','Open holdings · live/EOD price status')
for i,(sym,px,pnl,col) in enumerate([('RELIANCE','₹1,482.40','+1.24%',green),('HDFCBANK','₹1,736.20','−0.36%',red),('TCS','₹3,892.10','+0.82%',green)]):
 y=335+i*76; d.line((1140,y+56,1516,y+56),fill=line); text(d,(1142,y),sym,bold);text(d,(1142,y+28),'12 shares',small,muted);text(d,(1350,y),px,small);text(d,(1450,y),pnl,small,col)
rr(d,(1142,565,1516,602),blue,None,8);text(d,(1268,575),'Open portfolio',small,'#FFFFFF')
card(d,280,642,820,290,'Research ideas','Prioritized by setup quality · each action explains its inputs')
for i,(sym,desc,entry,sl,tgt) in enumerate([('INFY','Trend pullback · 78% setup confidence','₹1,840–1,862','₹1,796','₹1,945'),('ICICIBANK','Relative strength · 71% setup confidence','₹1,278–1,290','₹1,244','₹1,350')]):
 y=706+i*91; d.line((302,y+75,1078,y+75),fill=line);text(d,(304,y),sym,bold);text(d,(304,y+30),desc,small,muted);text(d,(684,y),'ENTRY '+entry,small);text(d,(826,y),'SL '+sl,small,red);text(d,(930,y),'TGT '+tgt,small,green);rr(d,(988,y+32,1062,y+64),blue,None,7);text(d,(1008,y+41),'Review',small,'#FFFFFF')
card(d,1120,642,418,290,'Data & alerts','Source and freshness shown beside every value')
for i,(a,b) in enumerate([('NSE bhavcopy','Updated 18:12 IST'),('Price feed','EOD · 27 Oct'),('Alerts','2 need review')]):
 y=710+i*58; text(d,(1144,y),a,bold);text(d,(1144,y+24),b,small,muted)
im.save(OUT/'wireframe_overview.png')
# portfolio
im,d=base('Portfolio','Portfolio');text(d,(280,96),'Primary portfolio  ·  8 open positions  ·  Values marked with source and timestamp',small,muted)
rr(d,(1256,88,1394,124),panel,line,8);text(d,(1275,98),'Export report',small,muted);rr(d,(1410,88,1538,124),blue,None,8);text(d,(1432,98),'+ Add trade',small,'#FFFFFF')
metric(d,280,140,285,'Invested','₹8,45,000','Capital deployed',ink);metric(d,583,140,285,'Market value','₹8,71,840','Last update 18:12',ink);metric(d,886,140,285,'Unrealized P&L','+₹26,840','+3.18%',green);metric(d,1189,140,349,'Available capital','₹3,55,000','No position count cap',blue)
card(d,280,270,1258,625,'Holdings','Search · filter by status/type/sector · sort columns · select rows')
# controls
rr(d,(302,329,630,369),'#F8FAFD',line,8);text(d,(320,340),'⌕  Search symbol or company',small,muted)
for x,w,label in [(646,112,'Open ▾'),(770,130,'All types ▾'),(910,132,'All sectors ▾')]:rr(d,(x,329,x+w,369),panel,line,8);text(d,(x+13,340),label,small,muted)
text(d,(1450,342),'Refresh  ↻',small,blue)
cols=[('HOLDING',315),('QTY',640),('AVG COST',730),('LTP / SOURCE',850),('INVESTED',1010),('P&L',1155),('ALLOCATION',1285),('ACTIONS',1435)]
for label,x in cols:text(d,(x,396),label,small,muted)
d.line((302,422,1516,422),fill=line)
rows=[('RELIANCE','Long · NSE','32','₹1,438.20','₹1,482.40','₹46,022','+₹1,414','8%'),('HDFCBANK','Long · NSE','50','₹1,742.50','₹1,736.20','₹87,125','−₹315','15%'),('TCS','Long · NSE','18','₹3,860.00','₹3,892.10','₹69,480','+₹578','12%'),('INFY','Long · NSE','42','₹1,812.00','₹1,840.50','₹76,104','+₹1,197','13%'),('SBIN','Long · NSE','75','₹812.20','₹824.90','₹60,915','+₹953','10%')]
for i,row in enumerate(rows):
 y=438+i*78
 if i%2==1:d.rectangle((302,y-8,1516,y+63),fill='#FAFBFD')
 text(d,(315,y),row[0],bold);text(d,(315,y+28),row[1],small,muted)
 for value,x in zip(row[2:], [640,730,850,1010,1155,1285]):text(d,(x,y+10),value,small,green if value.startswith('+') else red if value.startswith('−') else ink)
 rr(d,(1406,y,1486,y+32),'#FDEDEF','#F0C9CD',7);text(d,(1427,y+8),'Exit',small,red);text(d,(1492,y+7),'···',font,muted)
 d.line((302,y+66,1516,y+66),fill=line)
text(d,(306,842),'Exit opens a confirmation sheet: quantity, live/eod exit price, estimated fees, realized P&L.',small,muted)
text(d,(306,866),'Partial exit and edit levels are under the row overflow menu; confirm never executes silently.',small,muted)
im.save(OUT/'wireframe_portfolio.png')
