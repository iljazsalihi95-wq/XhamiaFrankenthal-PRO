import sys, sqlite3, os, shutil, datetime, hashlib, hmac, urllib.request, json
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QComboBox,QFileDialog,QMessageBox,QLineEdit,QDialog,QFormLayout,QFrame,QDoubleSpinBox
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QPixmap, QIcon, QColor, QBrush
from PySide6.QtWidgets import QHeaderView
from seed_data import seed
from finance_reports import report
from ledger_totals import summary
from receipts import create_receipt
from membership_rollover import carry_forward
from reportlab.platypus import SimpleDocTemplate,Table,TableStyle,Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4,landscape
ROOT=Path(os.getenv("APPDATA",str(Path.home())))/"XhamiaFrankenthalPRO"
ROOT.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect(ROOT/"xhamia.db")
db.execute("CREATE TABLE IF NOT EXISTS members(year INTEGER, member_id TEXT, first_name TEXT,last_name TEXT,method TEXT, jan TEXT,feb TEXT,mar TEXT,apr TEXT,may TEXT,jun TEXT,jul TEXT,aug TEXT,sep TEXT,oct TEXT,nov TEXT,dec TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS finance(year INTEGER,kind TEXT,date TEXT,description TEXT,method TEXT,category TEXT,amount TEXT)")
db.commit()
seed(db)
LOGO_URL="https://archive.org/download/20260126-152726-0000/20260126_152726_0000.png"
def mosque_logo():
 """Use the packaged official mosque logo offline; cache as fallback."""
 bundled=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))/"assets"/"mosque_logo.png"
 if bundled.exists():
  image=QPixmap(str(bundled))
  if not image.isNull():return image
 cache=ROOT/"mosque_logo.png"
 if cache.exists():return QPixmap(str(cache))
 return QPixmap()

class Login(QDialog):
 def __init__(self):
  super().__init__()
  self.setWindowTitle("Xhamia Frankenthal PRO | Hyrja e sigurt")
  self.setFixedSize(570,620)
  self.setObjectName("loginWindow")
  self.setStyleSheet("""
   QDialog#loginWindow {background:#071d35;color:#fff;font-family:'Segoe UI'}
   QLabel {color:#f2f6ff;background:transparent}
   QLineEdit {background:#f5f9ff;color:#102a47;border:2px solid #aac5df;border-radius:11px;padding:13px;font-size:16px;min-height:30px}
   QLineEdit:focus {border:2px solid #e3b951}
   QPushButton {background:#e6b74c;color:#102542;border:none;border-radius:12px;padding:15px;font-weight:800;font-size:17px;min-height:26px}
   QPushButton:hover {background:#f8ce6c}
  """)
  outer=QVBoxLayout(self);outer.setContentsMargins(48,24,48,30);outer.setSpacing(12)
  emblem=QLabel();emblem.setAlignment(Qt.AlignCenter);emblem.setFixedHeight(166)
  picture=mosque_logo()
  if not picture.isNull():
   emblem.setPixmap(picture.scaled(155,155,Qt.KeepAspectRatio,Qt.SmoothTransformation))
   self.setWindowIcon(QIcon(picture))
  else:emblem.setText("☪")
  outer.addWidget(emblem)
  heading=QLabel("XHAMIA FRANKENTHAL PRO");heading.setAlignment(Qt.AlignCenter)
  heading.setStyleSheet("color:#f4cc72;font-size:25px;font-weight:900")
  outer.addWidget(heading)
  subtitle=QLabel("ISLAMISCHER VEREIN FRANKENTHAL e.V.\nADMINISTRIMI I XHAMISË")
  subtitle.setAlignment(Qt.AlignCenter);subtitle.setStyleSheet("color:#c3d9ec;font-size:13px;letter-spacing:1px")
  outer.addWidget(subtitle)
  outer.addSpacing(18)
  user_label=QLabel("👤  PËRDORUESI");user_label.setStyleSheet("font-weight:700;font-size:13px")
  outer.addWidget(user_label)
  self.u=QLineEdit();self.u.setPlaceholderText("Shkruaj emrin e përdoruesit");outer.addWidget(self.u)
  pass_label=QLabel("🔒  FJALËKALIMI");pass_label.setStyleSheet("font-weight:700;font-size:13px")
  outer.addWidget(pass_label)
  self.p=QLineEdit();self.p.setEchoMode(QLineEdit.Password);self.p.setPlaceholderText("Shkruaj fjalëkalimin")
  self.p.returnPressed.connect(self.check);outer.addWidget(self.p)
  outer.addSpacing(14)
  b=QPushButton("HYR NË SISTEM  →");b.clicked.connect(self.check);outer.addWidget(b)
  note=QLabel("Të dhënat e xhamisë ruhen në kompjuter.\nQasje vetëm për administratorët.")
  note.setAlignment(Qt.AlignCenter);note.setStyleSheet("color:#a9bfd3;font-size:12px");outer.addWidget(note)
 def check(self):
  if self.u.text()=="XhamiaFrankenthal" and hmac.compare_digest(hashlib.sha256(self.p.text().encode()).hexdigest(),"4590c57bbe71fba3b0b4586e439d54f410eca68a7e1e17ba8f0f16b129d02b6f"):self.accept()
  else:QMessageBox.warning(self,"Gabim","Kredencialet nuk përputhen")
class Main(QMainWindow):
 def __init__(self):
  super().__init__();self.setWindowTitle("Xhamia Frankenthal PRO");self.resize(1500,880);self.setMinimumSize(1120,700)
  pic=mosque_logo()
  if not pic.isNull():self.setWindowIcon(QIcon(pic))
  w=QWidget();self.setCentralWidget(w);v=QVBoxLayout(w)
  v.setContentsMargins(22,16,22,18);v.setSpacing(14)
  self.hero=QLabel("XHAMIA FRANKENTHAL PRO\\nADMINISTRIMI I XHAMISË  •  REGJISTRIME DHE LLOGARITJE AUTOMATIKE")
  self.hero.setObjectName("heroTitle");self.hero.setAlignment(Qt.AlignCenter);self.hero.setMinimumHeight(174);v.addWidget(self.hero)
  self._hero_source=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))/"assets"/"mosque_interior.jpg"
  self._render_hero()
  body=QHBoxLayout();v.addLayout(body,1)
  sidebar=QFrame();sidebar.setObjectName("sidebar");sidebar.setFixedWidth(240)
  nav=QVBoxLayout(sidebar);nav.setContentsMargins(12,20,12,16);nav.setSpacing(10)
  logo=QLabel();logo.setAlignment(Qt.AlignCenter);logo.setMinimumHeight(118)
  if not pic.isNull():logo.setPixmap(pic.scaled(112,112,Qt.KeepAspectRatio,Qt.SmoothTransformation))
  else:logo.setText("IVF")
  nav.addWidget(logo)
  brand=QLabel("ISLAMISCHER VEREIN\\nFRANKENTHAL e.V.");brand.setWordWrap(True);brand.setAlignment(Qt.AlignCenter);brand.setStyleSheet("color:#e2c47c;font-weight:bold;font-size:13px");nav.addWidget(brand)
  for name in ("Ballina","Anëtarësia","Hyrjet","Daljet","Bilanci","Dëftesat","Hudbe & Derse","Historiku","Rregullorja","Mbledhjet","Procesverbalet"):
   icons={"Ballina":"⌂","Anëtarësia":"♟","Hyrjet":"↘","Daljet":"↗","Bilanci":"▥","Dëftesat":"▤","Hudbe & Derse":"▣"}
   button=QPushButton(icons.get(name,"◆")+"   "+name);button.setObjectName("navButton");button.setMinimumHeight(50)
   button.clicked.connect(lambda checked=False,n=name:self.navigate(n))
   nav.addWidget(button)
  nav.addStretch()
  body.addWidget(sidebar)
  workspace=QWidget();work=QVBoxLayout(workspace);work.setContentsMargins(8,0,0,0)
  body.addWidget(workspace,1)
  bar=QHBoxLayout();work.addLayout(bar)
  self.mode=QComboBox();self.mode.addItems(["Anëtarësia","Hyrjet","Daljet"]);bar.addWidget(self.mode)
  self.search=QLineEdit();self.search.setPlaceholderText("Kërko emër, mbiemër, përshkrim...");bar.addWidget(self.search,2)
  self.month_filter=QComboBox();self.month_filter.addItems(["Të gjithë muajt","Janar","Shkurt","Mars","Prill","Maj","Qershor","Korrik","Gusht","Shtator","Tetor","Nëntor","Dhjetor"]);bar.addWidget(self.month_filter)
  self.date_filter=QLineEdit();self.date_filter.setPlaceholderText("Data: DD.MM.VVVV");self.date_filter.setMaximumWidth(160);bar.addWidget(self.date_filter)
  self.clear_filter=QPushButton("Pastro");self.clear_filter.clicked.connect(self.reset_filters);bar.addWidget(self.clear_filter)
  self.year=QComboBox();self.year.addItems([str(x) for x in range(2015,2051)]);self.year.setCurrentText("2026");bar.addWidget(self.year)
  for label,func in [("Importo CSV",self.import_csv),("Eksporto PDF",self.pdf),("Backup",self.backup),("Dëftesë PDF",self.receipt_pdf),("Raport financiar A4",self.financial_pdf),("Rifresko",self.load)]:
   b=QPushButton(label);b.clicked.connect(func);bar.addWidget(b)
  self.dashboard=QLabel("SISTEMI I INTEGRUAR I ADMINISTRIMIT\\nAnëtarësia  •  Financat  •  Dokumentet  •  Arkiva")
  self.dashboard.setAlignment(Qt.AlignCenter);self.dashboard.setMinimumHeight(92);self.dashboard.setStyleSheet("font-size:22px;font-weight:800;color:#f4d27a;padding:20px;border:2px solid #c99c3b;border-radius:15px;background:#073d68")
  work.addWidget(self.dashboard)
  actions=QHBoxLayout();work.addLayout(actions)
  for label,callback in (("Shto anëtar",self.add_member),("Bart anëtarët në vitin pasues",self.rollover_members),("Regjistro hyrje",lambda:self.add_transaction("Hyrjet")),("Regjistro dalje",lambda:self.add_transaction("Daljet"))):
   btn=QPushButton(label);btn.clicked.connect(callback);actions.addWidget(btn)
  self.summary_label=QLabel("Raport nga të dhënat e importuara — pa rakordim bankar");self.summary_label.setObjectName("summary");work.addWidget(self.summary_label)
  self.stats=QHBoxLayout();work.addLayout(self.stats)
  self.stat_cards=[]
  for label,color in (("CASH","#0c8b5d"),("BANK","#1766ad"),("TË PAKLASIFIKUARA","#7548b7"),("TOTALI","#c88a16")):
   card=QLabel(label+"\\n—");card.setAlignment(Qt.AlignCenter);card.setObjectName("statCard")
   card.setStyleSheet(f"QLabel#statCard{{background:{color};color:white;border-radius:12px;padding:10px;font-weight:800;font-size:16px;min-height:60px}}")
   self.stats.addWidget(card);self.stat_cards.append(card)
  self.table=QTableWidget();self.table.setAlternatingRowColors(True);self.table.setMinimumHeight(390);self.table.verticalHeader().setDefaultSectionSize(43);self.table.verticalHeader().setVisible(False);self.table.setWordWrap(False);work.addWidget(self.table,3);self.mode.currentIndexChanged.connect(self.load);self.year.currentIndexChanged.connect(self.load)
  self.setStyleSheet("""
QMainWindow,QWidget{background:#eaf2fc;color:#102d50;font-family:'Segoe UI';font-size:13px}
QLabel#heroTitle{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #052744,stop:.48 #075082,stop:1 #10345d);color:#f6d47e;font-size:30px;font-weight:900;border-bottom:5px solid #d5a83c;border-radius:16px;padding:16px}
QFrame#sidebar{background:#082d55;border:2px solid #d4ae55;border-radius:17px}
QFrame#sidebar QLabel{background:transparent;color:#f3d17c}
QPushButton{background:#0864a2;border:1px solid #75b4e1;border-radius:10px;padding:11px;color:white;font-weight:700;font-size:13px;min-height:20px}
QPushButton:hover{background:#1883cc;border-color:#f0bf55}
QPushButton#navButton{background:#064373;text-align:left;padding-left:19px;font-size:15px;min-height:30px;border:1px solid #4da4d9}
QPushButton#navButton:hover{background:#d8a02d;color:#082e50}\nQLabel#summary{background:#d9eafa;color:#07385e;padding:10px;border:1px solid #8cbbe1;border-radius:10px;font-size:14px;font-weight:800}
QComboBox,QLineEdit{background:#fff;border:2px solid #a3c6e4;border-radius:9px;padding:9px;color:#10365b;min-height:22px}
QTableWidget{font-size:14px;background:#fff;alternate-background-color:#dceafb;gridline-color:#bfd5ec;selection-background-color:#86c5f3;selection-color:#06284b;border:2px solid #a7c8e5;border-radius:12px}
QTableWidget::item{padding:7px}
QHeaderView::section{background:#07508a;color:white;padding:12px;border:1px solid #3375a5;font-weight:bold;font-size:14px}
QScrollBar:vertical{background:#d8e8f8;width:14px}
QScrollBar::handle:vertical{background:#6d9ec4;border-radius:6px;min-height:24px}
QDialog{background:#eaf2fc;color:#102d50}
QStatusBar{background:#082d55;color:white;font-weight:bold}
""")
  self.search.textChanged.connect(self.apply_search)
  self.month_filter.currentIndexChanged.connect(self.apply_search)
  self.date_filter.textChanged.connect(self.apply_search)
  self.load()
 def resizeEvent(self,event):
  super().resizeEvent(event)
  self._render_hero()
 def _render_hero(self):
  if not hasattr(self,"hero"):return
  if getattr(self,"_hero_source",None) and self._hero_source.exists():
   photo=QPixmap(str(self._hero_source))
   if not photo.isNull():
    from PySide6.QtGui import QPainter,QLinearGradient
    canvas=photo.scaled(max(900,self.hero.width()),174,Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
    canvas=canvas.copy((canvas.width()-max(900,self.hero.width()))//2,0,max(900,self.hero.width()),174)
    painter=QPainter(canvas)
    gradient=QLinearGradient(0,0,canvas.width(),0)
    gradient.setColorAt(0,QColor(2,30,61,235));gradient.setColorAt(.45,QColor(2,37,76,160));gradient.setColorAt(1,QColor(3,35,70,185))
    painter.fillRect(canvas.rect(),gradient)
    from PySide6.QtGui import QFont
    painter.setPen(QColor("#f6d47e"))
    painter.setFont(QFont("Segoe UI",25,QFont.Bold))
    painter.drawText(canvas.rect().adjusted(18,10,-18,-50),Qt.AlignCenter,"XHAMIA FRANKENTHAL PRO")
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI",11,QFont.DemiBold))
    painter.drawText(canvas.rect().adjusted(18,78,-18,-8),Qt.AlignCenter,"ADMINISTRIMI I XHAMISË • REGJISTRIME DHE LLOGARITJE AUTOMATIKE")
    painter.end()
    self.hero.setPixmap(canvas)
    self.hero.setText("")
    self.hero.setToolTip("XHAMIA FRANKENTHAL PRO")
    return
  self.hero.setText("XHAMIA FRANKENTHAL PRO\\nADMINISTRIMI I XHAMISË • REGJISTRIME DHE LLOGARITJE AUTOMATIKE")
 def rollover_members(self):
  source=int(self.year.currentText())
  if source>=2050:
   QMessageBox.warning(self,"Vitet","Zgjidh një vit para 2050.");return
  target=source+1
  confirm=QMessageBox.question(self,"Bartja e anëtarëve",f"Të barten në {target} vetëm anëtarët që kanë paguar të paktën një muaj gjatë {source}? Pagesat nuk kopjohen.")
  if confirm!=QMessageBox.Yes:return
  try:
   added=carry_forward(db,source,target)
   self.year.setCurrentText(str(target));self.mode.setCurrentText("Anëtarësia");self.load()
   QMessageBox.information(self,"Bartja",f"U shtuan {added} anëtarë në {target}. Pagesat e reja janë bosh.")
  except Exception as exc:QMessageBox.critical(self,"Bartja",str(exc))
 def add_member(self):
  dialog=QDialog(self);dialog.setWindowTitle("Anëtar i ri");form=QFormLayout(dialog)
  inputs=[]
  for label in ("ID","Emri","Mbiemri","Metoda (Cash/Bank)"):
   field=QLineEdit();form.addRow(label,field);inputs.append(field)
  save=QPushButton("Ruaj anëtarin");form.addRow(save)
  def commit():
   values=[x.text().strip() for x in inputs]
   if not all(values[:3]):QMessageBox.warning(dialog,"Kontroll","ID, emri dhe mbiemri janë të detyrueshëm.");return
   db.execute("INSERT INTO members(year,member_id,first_name,last_name,method) VALUES (?,?,?,?,?)",(int(self.year.currentText()),*values))
   db.commit();dialog.accept();self.mode.setCurrentText("Anëtarësia");self.load()
  save.clicked.connect(commit);dialog.exec()
 def add_transaction(self,kind):
  dialog=QDialog(self);dialog.setWindowTitle("Regjistro "+kind);form=QFormLayout(dialog)
  fields=[]
  date=QLineEdit(datetime.date.today().strftime("%d.%m.%Y"));date.setPlaceholderText("DD.MM.VVVV")
  description=QLineEdit();description.setPlaceholderText("Përshkrimi i transaksionit")
  method=QComboBox();method.addItems(["Cash","Bank"])
  category=QComboBox();category.setEditable(True)
  categories=(["Anëtarësia","Donacion","Sadaka","Zekat","Fitër","Kurban","Aktivitete","Të ardhura të tjera"] if kind=="Hyrjet" else ["Qira","Rroga","Nebenkosten","Energji","Ujë","Mirëmbajtje","Pajisje","Aktivitete","Shpenzime të tjera"])
  category.addItems(categories)
  for label,widget in (("Data",date),("Përshkrimi",description),("Mënyra e pagesës",method),("Lloji / Kategoria",category)):
   form.addRow(label,widget)
  amount=QDoubleSpinBox();amount.setMaximum(10000000);amount.setDecimals(2);amount.setSuffix(" €");form.addRow("Shuma",amount)
  save=QPushButton("Ruaj regjistrimin");form.addRow(save)
  def commit():
   vals=[date.text().strip(),description.text().strip(),method.currentText(),category.currentText().strip()]
   try:datetime.datetime.strptime(vals[0],"%d.%m.%Y")
   except ValueError:QMessageBox.warning(dialog,"Data","Përdor DD.MM.VVVV");return
   if not vals[1] or not vals[3] or amount.value()<=0:QMessageBox.warning(dialog,"Kontroll","Plotëso përshkrimin, kategorinë dhe shumën më të madhe se zero.");return
   db.execute("INSERT INTO finance VALUES (?,?,?,?,?,?,?)",(int(self.year.currentText()),kind,*vals,f"{amount.value():.2f}"))
   db.commit();dialog.accept();self.mode.setCurrentText(kind);self.load()
  save.clicked.connect(commit);dialog.exec()
 def reset_filters(self):
  self.search.clear();self.date_filter.clear();self.month_filter.setCurrentIndex(0)
 def apply_search(self,*args):
  needle=self.search.text().strip().casefold()
  date_needle=self.date_filter.text().strip()
  month=self.month_filter.currentIndex()
  mode=self.mode.currentText()
  visible_count=0
  for i in range(self.table.rowCount()):
   cells=[self.table.item(i,j).text() if self.table.item(i,j) else "" for j in range(self.table.columnCount())]
   matches_text=not needle or any(needle in cell.casefold() for cell in cells)
   matches_date=not date_needle or (mode!="Anëtarësia" and bool(cells) and date_needle in cells[0])
   matches_month=month==0
   if month and mode!="Anëtarësia" and cells:
    try:
     date=datetime.datetime.strptime(cells[0],"%d.%m.%Y")
     matches_month=date.month==month
    except ValueError:
     try:
      date=datetime.datetime.strptime(cells[0],"%Y-%m-%d")
      matches_month=date.month==month
     except ValueError:matches_month=False
   if month and mode=="Anëtarësia":
    from seed_data import euros
    matches_month=len(cells)>month+3 and euros(cells[month+3])>0
   visible=matches_text and matches_date and matches_month
   self.table.setRowHidden(i,not visible)
   visible_count+=int(visible)
  if hasattr(self,"statusBar"):self.statusBar().showMessage(f"{visible_count} nga {self.table.rowCount()} regjistrime · {mode} · {self.year.currentText()}")
 def navigate(self,name):
  if name in ("Anëtarësia","Hyrjet","Daljet"):
   self.reset_filters()
   self.mode.setCurrentText(name)
   self.dashboard.setVisible(False)
  elif name=="Ballina":
   self.dashboard.setVisible(True)
  elif name=="Bilanci":
   self.show_balance()
  elif name=="Dëftesat":
   self.receipt_pdf()
  elif name=="Hudbe & Derse":
   QMessageBox.information(self,"Arkiva","Arkiva e plotë e hutbeve dhe derseve nuk është importuar ende.")
  elif name in ("Historiku","Rregullorja","Mbledhjet","Procesverbalet"):
   self.open_documents(name)
 def open_documents(self,section):
  """Editable mosque archive stored locally, with no placeholder-only buttons."""
  db.execute("CREATE TABLE IF NOT EXISTS mosque_documents (id INTEGER PRIMARY KEY AUTOINCREMENT, section TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL)")
  db.commit()
  from PySide6.QtWidgets import QListWidget,QTextEdit,QSplitter
  dialog=QDialog(self);dialog.setWindowTitle(section+" — Xhamia Frankenthal PRO");dialog.resize(1000,690)
  layout=QVBoxLayout(dialog)
  heading=QLabel(section.upper());heading.setStyleSheet("font-size:24px;font-weight:900;color:#07508a");layout.addWidget(heading)
  split=QSplitter(Qt.Horizontal);layout.addWidget(split,1)
  listing=QListWidget();listing.setMinimumWidth(270);split.addWidget(listing)
  editor=QWidget();form=QVBoxLayout(editor);split.addWidget(editor)
  title=QLineEdit();title.setPlaceholderText("Titulli i dokumentit");form.addWidget(title)
  body=QTextEdit();body.setPlaceholderText("Shkruaj tekstin e plotë të dokumentit ose procesverbalit...");form.addWidget(body,1)
  toolbar=QHBoxLayout();form.addLayout(toolbar)
  current=[None]
  def refresh():
   listing.clear()
   records=db.execute("SELECT id,title FROM mosque_documents WHERE section=? ORDER BY id DESC",(section,)).fetchall()
   for doc_id,doc_title in records:
    from PySide6.QtWidgets import QListWidgetItem
    item=QListWidgetItem(doc_title);item.setData(Qt.UserRole,doc_id);listing.addItem(item)
  def choose(item):
   current[0]=item.data(Qt.UserRole)
   row=db.execute("SELECT title,body FROM mosque_documents WHERE id=?",(current[0],)).fetchone()
   if row:title.setText(row[0]);body.setPlainText(row[1])
  def new():
   current[0]=None;listing.clearSelection();title.clear();body.clear()
  def save():
   t=title.text().strip();b=body.toPlainText().strip()
   if not t or not b:
    QMessageBox.warning(dialog,"Dokumenti","Titulli dhe përmbajtja janë të detyrueshme.");return
   if current[0]:
    db.execute("UPDATE mosque_documents SET title=?,body=? WHERE id=? AND section=?",(t,b,current[0],section))
   else:
    cur=db.execute("INSERT INTO mosque_documents(section,title,body,created_at) VALUES (?,?,?,?)",(section,t,b,datetime.datetime.now().isoformat()))
    current[0]=cur.lastrowid
   db.commit();refresh();QMessageBox.information(dialog,"U ruajt","Dokumenti u ruajt në arkivën lokale.")
  def export():
   if not title.text().strip():QMessageBox.warning(dialog,"PDF","Zgjidh dokumentin.");return
   path,_=QFileDialog.getSaveFileName(dialog,"Ruaj dokumentin",section+".pdf","PDF (*.pdf)")
   if not path:return
   from reportlab.platypus import Spacer
   from reportlab.lib.styles import ParagraphStyle
   from reportlab.lib.enums import TA_LEFT
   from xml.sax.saxutils import escape
   doc=SimpleDocTemplate(path,pagesize=A4)
   styles=getSampleStyleSheet()
   elements=[Paragraph(escape(title.text()),styles["Heading1"]),Spacer(1,16)]
   for line in body.toPlainText().splitlines():
    elements.append(Paragraph(escape(line) or " ",styles["Normal"]))
    elements.append(Spacer(1,6))
   doc.build(elements)
  for label,callback in (("Dokument i ri",new),("Ruaj ndryshimet",save),("Eksporto PDF",export)):
   button=QPushButton(label);button.clicked.connect(callback);toolbar.addWidget(button)
  listing.itemClicked.connect(choose)
  refresh();dialog.exec()
 def load(self):
  y=int(self.year.currentText());mode=self.mode.currentText()
  if mode=="Anëtarësia":
   heads=["ID","Emri","Mbiemri","Bank","Jan","Shk","Mar","Pri","Maj","Qer","Kor","Gush","Shta","Tet","Nën","Dhj"]
   rows=db.execute("""SELECT m.member_id,m.first_name,m.last_name,m.bank,
  MAX(CASE WHEN s.month=1 THEN s.raw_value END),
  MAX(CASE WHEN s.month=2 THEN s.raw_value END),
  MAX(CASE WHEN s.month=3 THEN s.raw_value END),
  MAX(CASE WHEN s.month=4 THEN s.raw_value END),
  MAX(CASE WHEN s.month=5 THEN s.raw_value END),
  MAX(CASE WHEN s.month=6 THEN s.raw_value END),
  MAX(CASE WHEN s.month=7 THEN s.raw_value END),
  MAX(CASE WHEN s.month=8 THEN s.raw_value END),
  MAX(CASE WHEN s.month=9 THEN s.raw_value END),
  MAX(CASE WHEN s.month=10 THEN s.raw_value END),
  MAX(CASE WHEN s.month=11 THEN s.raw_value END),
  MAX(CASE WHEN s.month=12 THEN s.raw_value END)
  FROM source_members m LEFT JOIN source_months s ON m.year=s.year AND m.source_row=s.source_row
  WHERE m.year=? GROUP BY m.year,m.source_row ORDER BY m.first_name,m.last_name""",(y,)).fetchall()
   extra=db.execute("SELECT member_id,first_name,last_name,method,jan,feb,mar,apr,may,jun,jul,aug,sep,oct,nov,dec FROM members WHERE year=?",(y,)).fetchall()
   rows=list(rows)+list(extra)
  else:
   heads=["Data","Përshkrimi","Cash/Bank","Kategoria","Shuma"]
   sheet=mode if y==2026 else f"{mode} {y}"
   rows=list(db.execute("SELECT date,description,account,category,printf('%.2f €',amount_cents/100.0) FROM source_finance WHERE source_sheet=? ORDER BY source_row",(sheet,)).fetchall())
   rows+=db.execute("SELECT date,description,method,category,amount FROM finance WHERE year=? AND kind=?",(y,mode)).fetchall()
  if mode=="Hyrjet":
   def is_membership(row):
    desc=str(row[1] or "").casefold()
    cat=str(row[3] or "").casefold()
    return any(word in (desc+" "+cat) for word in ("anëtarës","antares","pagesë bankare","pagese bankare"))
   rows=[row for row in rows if not is_membership(row)]
   path=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))/"data"/f"{y}.json"
   if path.exists():
    membership_rows=json.loads(path.read_text(encoding="utf-8")).get("rows",[])
    bank_row=next((r for r in membership_rows if r and "paguar përmes bank" in str(r[0]).casefold()),None)
    cash_row=next((r for r in membership_rows if r and "paguar në kesh" in str(r[0]).casefold()),None)
    months=("Janar","Shkurt","Mars","Prill","Maj","Qershor","Korrik","Gusht","Shtator","Tetor","Nëntor","Dhjetor")
    from seed_data import euros
    for m,month in enumerate(months):
     for method,source_row in (("Cash",cash_row),("Bank",bank_row)):
      if source_row and len(source_row)>m+4:
       amount=euros(source_row[m+4])
       if amount:
        rows.append((f"01.{m+1:02d}.{y}",f"Anëtarësia {month} {y} — {method}",method,"Anëtarësia",f"{amount/100:.2f} €"))
   def row_date(row):
    try:return datetime.datetime.strptime(str(row[0]),"%d.%m.%Y")
    except ValueError:return datetime.datetime.min
   rows.sort(key=row_date)
  self.table.setColumnCount(len(heads));self.table.setHorizontalHeaderLabels(heads);self.table.setRowCount(len(rows))
  for i,row in enumerate(rows):
   for j,val in enumerate(row):self.table.setItem(i,j,QTableWidgetItem(str(val or "")))
  header=self.table.horizontalHeader()
  header.setMinimumSectionSize(38)
  header.setStretchLastSection(False)
  if mode=="Anëtarësia":
   # Fit all twelve months on screen; identity columns get more space.
   header.setSectionResizeMode(QHeaderView.Stretch)
   for column in (0,3):
    header.setSectionResizeMode(column,QHeaderView.Fixed)
   self.table.setColumnWidth(0,52)
   self.table.setColumnWidth(3,55)
   self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
  else:
   header.setSectionResizeMode(QHeaderView.Stretch)
   header.setSectionResizeMode(1,QHeaderView.Interactive)
   self.table.setColumnWidth(1,280)
  self.apply_search()
  if mode in ("Hyrjet","Daljet"):
   from seed_data import euros
   cash=sum(euros(row[4]) for row in rows if str(row[2]).strip().casefold()=="cash")
   bank=sum(euros(row[4]) for row in rows if str(row[2]).strip().casefold()=="bank")
   other=sum(euros(row[4]) for row in rows if str(row[2]).strip().casefold() not in ("cash","bank"))
   values=(cash,bank,other,cash+bank+other)
   for label,card,value in zip(("CASH","BANK","TË PAKLASIFIKUARA","TOTALI"),self.stat_cards,values):
    card.setText(f"{label}\\n{value/100:,.2f} €")
  else:
   for card in self.stat_cards:card.setText("ANËTARËSIA\\nShih tabelën")
  self.statusBar().showMessage(f"{len(rows)} regjistrime · {mode} · {y}")
  if mode!="Anëtarësia":
   totals=summary(db,y)
   d=totals[mode]
   self.summary_label.setText(f"{mode} {y}: Cash {d['cash']/100:,.2f} € | Bank {d['bank']/100:,.2f} € | Të paklasifikuara {d['other']/100:,.2f} € | Përjashtuar {d['excluded']} rreshta")
  else:self.summary_label.setText(f"Anëtarësia {y}: {len(rows)} rreshta nga burimi zyrtar")
 def show_balance(self):
  y=int(self.year.currentText())
  from ledger_totals import summary as balance_summary
  try:
   values=balance_summary(db,y)
   incoming=values["Hyrjet"];outgoing=values["Daljet"]
   cash=incoming["cash"]-outgoing["cash"]
   bank=incoming["bank"]-outgoing["bank"]
   total=cash+bank
   details=QDialog(self);details.setWindowTitle(f"Bilanci ndër vite — {y}");details.resize(850,560)
   layout=QVBoxLayout(details)
   title=QLabel(f"BILANCI VJETOR {y}");title.setAlignment(Qt.AlignCenter)
   title.setStyleSheet("font-size:24px;color:#e2c47c;font-weight:bold;padding:16px")
   layout.addWidget(title)
   grid=QTableWidget(3,4)
   grid.setHorizontalHeaderLabels(["Llogaria","Hyrjet","Daljet","Diferenca"])
   for i,(label,inc,out) in enumerate((("Cash",incoming["cash"],outgoing["cash"]),("Bank",incoming["bank"],outgoing["bank"]),("Gjithsej",incoming["cash"]+incoming["bank"],outgoing["cash"]+outgoing["bank"]))):
    for j,value in enumerate((label,f"{inc/100:,.2f} €",f"{out/100:,.2f} €",f"{(inc-out)/100:,.2f} €")):
     grid.setItem(i,j,QTableWidgetItem(value))
   grid.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
   layout.addWidget(grid)
   notice=QLabel("Diferencat janë lëvizje të regjistruara, jo domosdoshmërisht gjendja reale e bankës.\\nGjendjet fillestare dhe rakordimet duhet të kontrollohen veçmas.")
   notice.setWordWrap(True);layout.addWidget(notice)
   buttons=QHBoxLayout();layout.addLayout(buttons)
   export=QPushButton("Eksporto raportin PDF");export.clicked.connect(self.financial_pdf);buttons.addWidget(export)
   close=QPushButton("Mbyll");close.clicked.connect(details.accept);buttons.addWidget(close)
   details.exec()
  except Exception as exc:QMessageBox.critical(self,"Bilanci",str(exc))
 def receipt_pdf(self):
  mode=self.mode.currentText()
  i=self.table.currentRow()
  if i<0:
   QMessageBox.warning(self,"Dëftesa","Zgjidh një anëtar ose një pagesë në tabelë.");return
  year=self.year.currentText()
  if mode=="Anëtarësia":
   name=" ".join(self.table.item(i,j).text() for j in (1,2) if self.table.item(i,j))
   months=["Janar","Shkurt","Mars","Prill","Maj","Qershor","Korrik","Gusht","Shtator","Tetor","Nëntor","Dhjetor"]
   paid=[]
   for month in range(12):
    item=self.table.item(i,month+4)
    raw=item.text().strip() if item else ""
    from seed_data import euros
    if euros(raw)>0:paid.append((months[month],raw))
   if not paid:
    QMessageBox.information(self,"Dëftesa","Ky anëtar nuk ka pagesa të regjistruara për këtë vit.");return
   choose=QDialog(self);choose.setWindowTitle("Dëftesë anëtarësie")
   form=QFormLayout(choose)
   person=QLabel(name+" — "+year);form.addRow("Anëtari",person)
   month_select=QComboBox()
   for month,amount in paid:month_select.addItem(f"{month}: {amount}",(month,amount))
   form.addRow("Pagesa",month_select)
   confirm=QPushButton("Krijo PDF");form.addRow(confirm);confirm.clicked.connect(choose.accept)
   if choose.exec()!=QDialog.Accepted:return
   month,amount=month_select.currentData()
   fields=[month+" "+year,name,"Anëtarësia",amount]
   from receipts import create_membership_receipt
   p,_=QFileDialog.getSaveFileName(self,"Ruaj dëftesën",f"Deftese_{year}_{month}.pdf","PDF (*.pdf)")
   if not p:return
   try:
    create_membership_receipt(p,year,name,month,amount)
    QMessageBox.information(self,"Dëftesa","Dëftesa e anëtarësisë u ruajt si PDF.")
   except Exception as exc:QMessageBox.critical(self,"Dëftesa",str(exc))
   return
  if mode!="Hyrjet":
   QMessageBox.information(self,"Dëftesa","Për dëftesë hyrjeje zgjidh një regjistrim te Hyrjet.");return
  fields=[self.table.item(i,j).text() if self.table.item(i,j) else "" for j in range(5)]
  p,_=QFileDialog.getSaveFileName(self,"Ruaj dëftesën","Deftese_Xhamia.pdf","PDF (*.pdf)")
  if not p:return
  try:
   create_receipt(p,year,fields)
   QMessageBox.information(self,"Dëftesa","PDF u ruajt.")
  except Exception as e:QMessageBox.critical(self,"Dëftesa",str(e))
 def financial_pdf(self):
  p,_=QFileDialog.getSaveFileName(self,"Ruaj raportin financiar",f"Raporti_financiar_{self.year.currentText()}.pdf","PDF (*.pdf)")
  if not p:return
  try:
   report(db,int(self.year.currentText()),p)
   QMessageBox.information(self,"Raporti","Raporti financiar A4 u ruajt.")
  except Exception as e:QMessageBox.critical(self,"Raporti",str(e))
 def backup(self):
  target,_=QFileDialog.getSaveFileName(self,"Ruaj kopjen e sigurisë",f"XhamiaFrankenthal_{datetime.date.today().isoformat()}.sqlite3","SQLite (*.sqlite3)")
  if not target:return
  try:
   with sqlite3.connect(target) as backup_db:db.backup(backup_db)
   QMessageBox.information(self,"Backup","Kopja e sigurisë u ruajt.")
  except Exception as e:QMessageBox.critical(self,"Backup",str(e))
 def import_csv(self):
  import csv
  p,_=QFileDialog.getOpenFileName(self,"Zgjidh CSV","","CSV (*.csv)")
  if not p:return
  try:
   with open(p,encoding="utf-8-sig",newline="") as f:rows=list(csv.reader(f))
   y=int(self.year.currentText());mode=self.mode.currentText()
   for row in rows[1:]:
    if mode=="Anëtarësia" and len(row)>=16:db.execute("INSERT INTO members VALUES ("+",".join(["?"]*17)+")",[y]+row[:16])
    elif mode!="Anëtarësia" and len(row)>=5:db.execute("INSERT INTO finance VALUES (?,?,?,?,?,?,?)",[y,mode]+row[:5])
   db.commit();self.load()
  except Exception as e:QMessageBox.critical(self,"Importi",str(e))
 def pdf(self):
  p,_=QFileDialog.getSaveFileName(self,"Ruaj PDF",f"{self.mode.currentText()}_{self.year.currentText()}.pdf","PDF (*.pdf)")
  if not p:return
  try:
   data=[[self.table.horizontalHeaderItem(j).text() for j in range(self.table.columnCount())]]
   for i in range(self.table.rowCount()):data.append([(self.table.item(i,j).text() if self.table.item(i,j) else "") for j in range(self.table.columnCount())])
   doc=SimpleDocTemplate(p,pagesize=landscape(A4));styles=getSampleStyleSheet()
   t=Table(data,repeatRows=1,hAlign="LEFT");t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#193c58")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTSIZE",(0,0),(-1,-1),6),("GRID",(0,0),(-1,-1),.25,colors.grey)]))
   doc.build([Paragraph("Xhamia Frankenthal - "+self.mode.currentText()+" "+self.year.currentText(),styles["Heading1"]),t])
  except Exception as e:QMessageBox.critical(self,"PDF",str(e))
app=QApplication(sys.argv)
login=Login()
if login.exec()==QDialog.Accepted:
 win=Main();win.show();sys.exit(app.exec())
