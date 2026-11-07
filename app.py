import sys, sqlite3, os, datetime, hashlib, hmac, tempfile, shutil
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QComboBox,QFileDialog,QMessageBox,QLineEdit,QDialog,QFormLayout,QFrame,QDoubleSpinBox,QDateEdit,QMenu,QScrollArea,QAbstractItemView,QStyle,QSizePolicy
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, Qt, QUrl, QSize, QDate, QTimer, QRectF
from PySide6.QtGui import QPixmap, QIcon, QColor, QBrush, QDesktopServices, QPainter, QPainterPath, QLinearGradient
from PySide6.QtWidgets import QHeaderView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from seed_data import seed
from finance_reports import report
from buchhaltung import Buchhaltung
from ledger_totals import summary, records, totals, exclusion, reconciliation
from receipts import create_receipt
from membership_rollover import carry_forward
from sheet_source import SHEET, TABS, backup_database, import_workbook
from reportlab.platypus import SimpleDocTemplate,Table,TableStyle,Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4,landscape
ROOT=Path(os.getenv("APPDATA",str(Path.home())))/"XhamiaFrankenthalPRO"
ROOT.mkdir(parents=True,exist_ok=True)
database_path=ROOT/"xhamia.db"
existing_database=database_path.exists()
db=sqlite3.connect(database_path)
upgrade_backup=ROOT/"para-perditesimit-v2.sqlite3"
if existing_database and not upgrade_backup.exists():
 backup_database(db,upgrade_backup)
db.execute("CREATE TABLE IF NOT EXISTS members(year INTEGER, member_id TEXT, first_name TEXT,last_name TEXT,method TEXT, jan TEXT,feb TEXT,mar TEXT,apr TEXT,may TEXT,jun TEXT,jul TEXT,aug TEXT,sep TEXT,oct TEXT,nov TEXT,dec TEXT)")
db.execute("CREATE TABLE IF NOT EXISTS finance(year INTEGER,kind TEXT,date TEXT,description TEXT,method TEXT,category TEXT,amount TEXT)")
db.commit()
seed(db)
ASSETS=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))/"assets"
def mosque_logo():
 """Use the packaged official mosque logo offline; cache as fallback."""
 bundled=ASSETS/"mosque_logo.png"
 if bundled.exists():
  image=QPixmap(str(bundled))
  if not image.isNull():return image
 cache=ROOT/"mosque_logo.png"
 if cache.exists():return QPixmap(str(cache))
 return QPixmap()

class Login(QDialog):
 def __init__(self):
  super().__init__()
  self.setWindowTitle("Xhamia Frankenthal PRO — Hyrja")
  self.setFixedSize(680,490)
  self.setObjectName("loginWindow")
  picture=mosque_logo()
  self.setWindowIcon(QIcon(picture))
  outer=QHBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)

  brand=QFrame();brand.setObjectName("loginBrand");brand.setFixedWidth(242)
  brand_layout=QVBoxLayout(brand);brand_layout.setContentsMargins(18,24,18,24)
  brand_layout.addStretch()
  emblem=QLabel();emblem.setAlignment(Qt.AlignCenter)
  emblem.setPixmap(picture.scaled(144,144,Qt.KeepAspectRatio,Qt.SmoothTransformation))
  brand_layout.addWidget(emblem)
  brand_title=QLabel("XHAMIA FRANKENTHAL");brand_title.setObjectName("loginBrandTitle")
  brand_title.setAlignment(Qt.AlignCenter);brand_title.setWordWrap(True);brand_layout.addWidget(brand_title)
  brand_subtitle=QLabel("ISLAMISCHER VEREIN\nFRANKENTHAL e.V.")
  brand_subtitle.setAlignment(Qt.AlignCenter);brand_layout.addWidget(brand_subtitle)
  brand_layout.addStretch()
  outer.addWidget(brand)

  panel=QWidget();form=QVBoxLayout(panel);form.setContentsMargins(34,30,34,28);form.setSpacing(9)
  form.addStretch()
  heading=QLabel("Hyr në program");heading.setObjectName("loginHeading");form.addWidget(heading)
  subtitle=QLabel("Administrimi i Xhamisë Frankenthal");form.addWidget(subtitle)
  form.addSpacing(13)
  self.u=QLineEdit();self.u.setPlaceholderText("Emri i përdoruesit")
  self.p=QLineEdit();self.p.setEchoMode(QLineEdit.Password);self.p.setPlaceholderText("Fjalëkalimi")
  for title,field in (("Përdoruesi",self.u),("Fjalëkalimi",self.p)):
   label=QLabel(title);label.setObjectName("loginField");label.setBuddy(field)
   form.addWidget(label);form.addWidget(field)
  self.error=QLabel();self.error.setObjectName("loginError")
  self.error.setFixedHeight(20);form.addWidget(self.error)
  for field in (self.u,self.p):field.textEdited.connect(self.error.clear)
  button=QPushButton("Hyr në program  →");button.setDefault(True);button.clicked.connect(self.check)
  form.addWidget(button)
  form.addStretch()
  version=QLabel("Xhamia Frankenthal PRO   ·   Windows");version.setObjectName("loginVersion")
  form.addWidget(version);outer.addWidget(panel,1)
  self.setStyleSheet("""
   QDialog#loginWindow {background:#f5f9ff;font-family:'Segoe UI';font-size:14px}
   QLabel {color:#153656;background:transparent}
   QFrame#loginBrand {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #082848,stop:1 #0a5685);border-right:3px solid #dfb44f}
   QFrame#loginBrand QLabel {color:#deecfa}
   QFrame#loginBrand QLabel#loginBrandTitle {color:#ffda7c;font-size:17px;font-weight:800;padding-top:15px}
   QLabel#loginHeading {font-size:32px;font-weight:800;color:#0b3054}
   QLabel#loginField {font-weight:700}
   QLabel#loginError {color:#a31e36;font-size:12px}
   QLabel#loginVersion {color:#536a80;font-size:12px}
   QLineEdit {background:#fff;color:#102a47;border:1px solid #a3bed8;border-radius:9px;padding:10px;font-size:15px;min-height:20px}
   QLineEdit:focus {border:2px solid #1267a0}
   QPushButton {background:#0b5185;color:#fff;border:1px solid #063759;border-radius:10px;padding:12px;font-weight:800;font-size:15px}
   QPushButton:hover {background:#126eaa}
  """)
  self.u.setFocus()
 def check(self):
  if self.u.text()=="XhamiaFrankenthal" and hmac.compare_digest(hashlib.sha256(self.p.text().encode()).hexdigest(),"4590c57bbe71fba3b0b4586e439d54f410eca68a7e1e17ba8f0f16b129d02b6f"):
   self.accept()
  else:
   self.error.setText("Përdoruesi ose fjalëkalimi nuk përputhet.")
   self.p.setFocus();self.p.selectAll()

NAV_SYMBOLS={
 "Ballina":"M2 11l10-9 10 9M5 10v11h5v-7h4v7h5V10",
 "Anëtarësia":"M12 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6M5 11a2 2 0 1 0 0-4M19 11a2 2 0 1 0 0-4M6 21v-3a6 6 0 0 1 12 0v3zM2 20v-3a4 4 0 0 1 3-4m17 7v-3a4 4 0 0 0-3-4",
 "Hyrjet":"M3 7a9 4 0 1 0 18 0 9 4 0 1 0-18 0m0 0v11c0 5 18 5 18 0V7M3 11c0 5 18 5 18 0M3 15c0 5 18 5 18 0",
 "Daljet":"M7 21V3L2 8m5-5 5 5m5-5v18l-5-5m5 5 5-5",
 "Bilanci":"M3 21v-7h4v7zm7 0V9h4v12zm7 0V3h4v18z",
 "Dëftesat":"M5 2h9l5 5v15H5zM14 2v6h5M8 12h8m-8 4h8",
 "Hudbe & Derse":"M12 5v16m0 0c-3-3-6-4-10-3V3c4-1 7 0 10 2 3-2 6-3 10-2v15c-4-1-7 0-10 3",
 "Cilësimet":"M9 3h6l1 3 3 1 2 4-2 2v4l-4 3-3-1-3 1-4-3v-4l-2-2 2-4 3-1zM15 12a3 3 0 1 0-6 0 3 3 0 0 0 6 0",
}

def symbol_icon(name):
 path=NAV_SYMBOLS[name]
 color="#fb4d51" if name=="Daljet" else "#f6faff"
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="{path}" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
 renderer=QSvgRenderer(QByteArray(svg.encode()))
 canvas=QPixmap(64,64);canvas.fill(Qt.transparent)
 painter=QPainter(canvas);renderer.render(painter);painter.end()
 return QIcon(canvas)

class MosqueHeader(QWidget):
 def __init__(self,logo):
  super().__init__()
  self.photo=QPixmap(str(ASSETS/"reference_panorama.jpg"))
  self.setFixedHeight(287)
  self.title=QLabel("XHAMIA FRANKENTHAL PRO",self)
  self.title.setObjectName("heroTitle")
  self.title.setAlignment(Qt.AlignCenter)
  self.subtitle=QLabel("ADMINISTRIMI I XHAMISË   •   REGJISTRIME DHE LLOGARITJE AUTOMATIKE",self)
  self.subtitle.setObjectName("tagline")
  self.subtitle.setAlignment(Qt.AlignCenter)
  self.emblem=QLabel(self)
  self.emblem.setAlignment(Qt.AlignCenter)
  # The official asset includes the photographic surroundings of the seal.
  seal=QPixmap(184,184);seal.fill(Qt.transparent)
  painter=QPainter(seal);painter.setRenderHint(QPainter.Antialiasing)
  circle=QPainterPath();circle.addEllipse(QRectF(1,1,182,182))
  painter.setClipPath(circle)
  painter.drawPixmap(QRectF(0,0,184,184),logo,QRectF(3,13,350,345))
  painter.end()
  self.emblem.setPixmap(seal)
  self.association=QLabel("ISLAMISCHER VEREIN\nFRANKENTHAL e.V.",self)
  self.association.setObjectName("association")
  self.association.setAlignment(Qt.AlignCenter)

 def resizeEvent(self,event):
  super().resizeEvent(event)
  width=self.width()-250
  self.emblem.setGeometry(0,0,250,187)
  self.association.setGeometry(0,188,250,52)
  self.title.setGeometry(250,198,width,51)
  self.title.setStyleSheet(f"font-size:{min(39, width//25)}px")
  self.subtitle.setStyleSheet(f"font-size:{min(16, width//69)}px")
  self.subtitle.setGeometry(250,250,width,33)

 def paintEvent(self,event):
  painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing)
  painter.setRenderHint(QPainter.SmoothPixmapTransform)
  width=self.width()
  blue=QLinearGradient(0,0,0,287)
  blue.setColorAt(0,QColor("#031f40"));blue.setColorAt(1,QColor("#075084"))
  painter.fillRect(QRectF(0,0,width,287),blue)
  painter.save()
  painter.translate(250,0)
  painter.scale((width-250)/1285,1)
  painter.translate(-251,0)
  edge=QPainterPath()
  edge.moveTo(251,0);edge.lineTo(1536,0);edge.lineTo(1536,121)
  edge.cubicTo(1450,217,1320,252,1180,253)
  edge.lineTo(525,253);edge.cubicTo(408,190,342,222,251,241)
  edge.closeSubpath()
  painter.setClipPath(edge)
  painter.drawPixmap(QRectF(251,0,1285,210),self.photo,QRectF(self.photo.rect()))
  fade=QLinearGradient(0,174,0,211)
  fade.setColorAt(0,QColor(4,53,91,0));fade.setColorAt(1,QColor("#04355b"))
  painter.fillRect(QRectF(251,174,1285,37),fade)
  painter.restore()
  ribbon=QPainterPath()
  ribbon.moveTo(0,205);ribbon.cubicTo(158,330,337,149,528,254)
  ribbon.cubicTo(346,177,161,342,0,205)
  left_ribbon=QPainterPath(ribbon)
  ribbon=QPainterPath()
  ribbon.moveTo(1180,253);ribbon.cubicTo(1330,248,1460,203,1536,121)
  ribbon.lineTo(1536,151);ribbon.cubicTo(1450,228,1330,258,1180,253)
  gold=QLinearGradient(0,198,0,270)
  gold.setColorAt(0,QColor("#ffeb9c"));gold.setColorAt(.65,QColor("#f9d878"));gold.setColorAt(1,QColor("#b98424"))
  painter.fillPath(left_ribbon,gold)
  painter.translate(250,0)
  painter.scale((width-250)/1285,1)
  painter.translate(-251,0)
  painter.fillPath(ribbon,gold)

class DocumentPage(QWebEnginePage):
 def acceptNavigationRequest(self,url,kind,main_frame):
  if kind==QWebEnginePage.NavigationType.NavigationTypeLinkClicked and url.scheme() in ("http","https","mailto"):
   QDesktopServices.openUrl(url)
   return False
  return super().acceptNavigationRequest(url,kind,main_frame)

class HtmlDocument(QDialog):
 def __init__(self,parent,title,path,section="",archive=None):
  super().__init__(parent)
  self.setWindowTitle(title)
  self.resize(1170,810)
  layout=QVBoxLayout(self)
  if archive:
   button=QPushButton("Hap arkivën lokale")
   button.clicked.connect(archive)
   layout.addWidget(button)
  self.view=QWebEngineView(self)
  self.view.setPage(DocumentPage(parent.document_profile,self.view))
  self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,True)
  self.view.page().newWindowRequested.connect(self.open_external)
  parent.document_profile.downloadRequested.connect(self.save_download)
  self.view.printRequested.connect(self.save_pdf)
  self.view.printRequestedByFrame.connect(self.save_pdf)
  self.view.pdfPrintingFinished.connect(self.pdf_finished)
  layout.addWidget(self.view)
  url=QUrl.fromLocalFile(str(path))
  url.setFragment(section)
  self.view.load(url)

 def open_external(self,request):
  url=request.requestedUrl()
  if url.scheme() in ("http","https","mailto"):
   QDesktopServices.openUrl(url)

 def save_download(self,request):
  if request.page()!=self.view.page():
   return
  suggested=Path(request.downloadDirectory())/request.downloadFileName()
  target,_=QFileDialog.getSaveFileName(self,"Ruaj dokumentin",str(suggested))
  if target:
   path=Path(target)
   request.setDownloadDirectory(str(path.parent))
   request.setDownloadFileName(path.name)
   request.accept()

 def save_pdf(self,frame=None):
  target,_=QFileDialog.getSaveFileName(self,"Ruaj PDF",self.windowTitle()+".pdf","PDF (*.pdf)")
  if target:
   (frame if frame is not None else self.view).printToPdf(target)

 def pdf_finished(self,path,success):
  if not success:
   QMessageBox.warning(self,"PDF","Dokumenti nuk u ruajt si PDF.")

class Main(QMainWindow):
 def __init__(self):
  super().__init__();self.setWindowTitle("Xhamia Frankenthal PRO — Administrimi i Xhamisë");self.resize(1536,830);self.setMinimumSize(1080,690)
  pic=mosque_logo()
  if not pic.isNull():self.setWindowIcon(QIcon(pic))
  w=QWidget();self.setCentralWidget(w);v=QVBoxLayout(w)
  v.setContentsMargins(0,0,0,0);v.setSpacing(0)
  self.hero=MosqueHeader(pic);v.addWidget(self.hero)
  body=QHBoxLayout();body.setSpacing(7);body.setContentsMargins(0,0,8,5);v.addLayout(body,1)
  sidebar=QFrame();sidebar.setObjectName("sidebar")
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFixedWidth(240);scroll.setFrameShape(QFrame.NoFrame)
  scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);scroll.setWidget(sidebar)
  nav=QVBoxLayout(sidebar);nav.setContentsMargins(13,0,3,6);nav.setSpacing(4)
  self.nav_buttons={}
  for name,icon in (
   ("Ballina",QStyle.SP_DirHomeIcon),("Anëtarësia",QStyle.SP_DirOpenIcon),
   ("Hyrjet",QStyle.SP_ArrowDown),("Daljet",QStyle.SP_ArrowUp),
   ("Bilanci",QStyle.SP_ComputerIcon),("Dëftesat",QStyle.SP_FileIcon),
   ("Hudbe & Derse",QStyle.SP_DirIcon),("Cilësimet",QStyle.SP_FileDialogDetailedView),
   ("Buchhaltung",QStyle.SP_FileDialogDetailedView),("Vërtetimi i pagesave vjetore",QStyle.SP_FileDialogDetailedView),("Sistemi i Hoxhës",QStyle.SP_DirHomeIcon),("Historiku",QStyle.SP_FileDialogInfoView),
   ("Rregullorja",QStyle.SP_FileIcon),("Mbledhjet",QStyle.SP_DirIcon),
   ("Procesverbalet",QStyle.SP_FileIcon)
  ):
   button=QPushButton({"Hudbe & Derse":"Hudbe / Derse","Vërtetimi i pagesave vjetore":"Anlage 14"}.get(name,name));button.setToolTip(name);button.setObjectName("navButton");button.setCheckable(True)
   button.setIcon(symbol_icon(name) if name in NAV_SYMBOLS else self.style().standardIcon(icon));button.setIconSize(QSize(29,29))
   button.setFixedHeight(53)
   button.clicked.connect(lambda checked=False,n=name:self.navigate(n))
   nav.addWidget(button);self.nav_buttons[name]=button
  nav.addStretch()
  body.addWidget(scroll)
  workspace=QFrame();workspace.setObjectName("workspace");work=QVBoxLayout(workspace);work.setContentsMargins(10,8,10,8);work.setSpacing(6)
  body.addWidget(workspace,1)
  bar=QHBoxLayout();work.addLayout(bar)
  self.mode=QComboBox();self.mode.setObjectName("toolbarSelect");self.mode.setMinimumWidth(126);self.mode.addItems(["Anëtarësia","Hyrjet","Daljet"]);bar.addWidget(self.mode)
  self.search=QLineEdit();self.search.setPlaceholderText("Kërko emër, mbiemër, përshkrim...");bar.addWidget(self.search,2)
  self.year=QComboBox();self.year.setObjectName("toolbarSelect");self.year.setMinimumWidth(90);self.year.addItems([str(x) for x in range(2015,2051)]);self.year.setCurrentText("2026");bar.addWidget(self.year)
  for label,func,tone in [("Importo CSV",self.import_csv,"green"),("Eksporto PDF",self.pdf,"red"),("Backup",self.backup,"blue")]:
   b=QPushButton(label);b.setProperty("tone",tone);b.clicked.connect(func);bar.addWidget(b)
  self.dashboard=QLabel("SISTEMI I INTEGRUAR I ADMINISTRIMIT\\nAnëtarësia  •  Financat  •  Dokumentet  •  Arkiva")
  self.dashboard.setAlignment(Qt.AlignCenter);self.dashboard.setMinimumHeight(72);self.dashboard.setStyleSheet("font-size:22px;font-weight:800;color:#f4d27a;padding:20px;border:2px solid #c99c3b;border-radius:15px;background:#073d68")
  work.addWidget(self.dashboard)
  actions=QHBoxLayout();work.addLayout(actions)
  for label,callback,tone in (
   ("Shto hyrje",self.add_record,"green"),
   ("Bart anëtarët në vitin pasues",self.rollover_members,"blue"),("Regjistro hyrje",self.add_record,"purple"),
   ("Raport financiar A4",self.financial_pdf,"gold")
  ):
   btn=QPushButton(label);btn.setProperty("tone",tone);btn.clicked.connect(callback);actions.addWidget(btn)
   if tone=="green":self.add_button=btn
   if tone=="purple":self.register_button=btn
  filter_panel=QFrame();filter_panel.setObjectName("filters");work.addWidget(filter_panel)
  filters=QHBoxLayout(filter_panel);filters.setContentsMargins(8,4,8,4)
  self.filter_label=QLabel("Filtrimi");self.filter_label.setObjectName("filterLabel");filters.addWidget(self.filter_label)
  self.month_filter=QComboBox();self.month_filter.addItems(["Të gjithë muajt","Janar","Shkurt","Mars","Prill","Maj","Qershor","Korrik","Gusht","Shtator","Tetor","Nëntor","Dhjetor"])
  self.date_from=QDateEdit();self.date_to=QDateEdit()
  for label,field in (("Nga data",self.date_from),("Deri më",self.date_to)):
   field.setCalendarPopup(True);field.setDisplayFormat("dd.MM.yyyy");field.setMinimumWidth(113)
   filters.addWidget(QLabel(label));filters.addWidget(field)
  filters.addWidget(QLabel("Muaji"));filters.addWidget(self.month_filter,1)
  self.month_filter.setMaximumWidth(235)
  self.clear_filter=QPushButton("⟳  Pastro filtrat");self.clear_filter.setObjectName("clearFilters");self.clear_filter.clicked.connect(self.reset_filters);filters.addWidget(self.clear_filter)
  self.reset_date_range()
  self.summary_label=QLabel();self.statusBar().addPermanentWidget(self.summary_label)
  self.stats=QHBoxLayout();work.addLayout(self.stats)
  self.stat_cards=[]
  for label,color in (("Cash","#b5ead5"),("Bank","#a8d8ff"),("Të paklasifikuara","#e0cbff"),("Totali","#ffda82")):
   card=QLabel(label+"\\n—");card.setAlignment(Qt.AlignCenter);card.setObjectName("statCard")
   card.setStyleSheet(f"QLabel#statCard{{background:{color};color:#10284d;border:1px solid #92aec9;border-radius:10px;padding:6px;font-weight:800;font-size:16px;min-height:45px}}")
   self.stats.addWidget(card);self.stat_cards.append(card)
  self.table=QTableWidget();self.table.setAlternatingRowColors(True);self.table.setMinimumHeight(95);self.table.verticalHeader().setDefaultSectionSize(31);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.doubleClicked.connect(self.edit_record);self.table.setWordWrap(False);work.addWidget(self.table,3);self.mode.currentIndexChanged.connect(self.load);self.year.currentIndexChanged.connect(self.year_changed)
  self.table.setContextMenuPolicy(Qt.CustomContextMenu)
  self.table.customContextMenuRequested.connect(self.record_menu)
  self.setStyleSheet("""
QMainWindow{background:#073456} QWidget{color:#102d50;font-family:'Segoe UI';font-size:13px}
QLabel#heroTitle,QLabel#tagline,QLabel#association{background:transparent}
QLabel#association{color:#f9d77b;font-weight:800;font-size:19px}
QFrame#workspace{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #a7d2f2,stop:.44 #d8ecff,stop:1 #f1f8ff);border:2px solid #8abce3;border-radius:19px}
QFrame#filters{background:#dceeff;border:1px solid #accdea;border-radius:8px}
QLabel#filterLabel{font-weight:800}
QLabel#heroTitle{font-size:39px;font-weight:900;padding:3px;color:#f9d77b}
QLabel#tagline{font-size:16px;color:white;padding:7px;letter-spacing:1px}
QPushButton[tone="green"]{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #22bb58,stop:1 #087337)}
QPushButton[tone="red"]{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #f34b58,stop:1 #a80c2a)}
QPushButton[tone="purple"]{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #9258d1,stop:1 #502388)}
QPushButton[tone="gold"]{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffab23,stop:1 #b96400)}
QPushButton[tone="blue"]{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1b81c8,stop:1 #053b68)}
QFrame#sidebar{background:#062f58}
QFrame#sidebar QLabel{background:transparent;color:#f3d17c}
QPushButton{background:#0864a2;border:1px solid #75b4e1;border-radius:10px;padding:9px;color:white;font-weight:700;font-size:13px;min-height:20px}
QPushButton:hover{background:#1883cc;border-color:#f0bf55}
QPushButton#navButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0d75b6,stop:1 #042a4e);text-align:left;padding-left:17px;font-size:17px;min-height:24px;padding-top:8px;padding-bottom:8px;border:1px solid #4da4d9}
QPushButton#navButton:hover,QPushButton#navButton:checked{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffe36e,stop:1 #ce860a);color:#082e50}\nQLabel#summary{background:#d9eafa;color:#07385e;padding:10px;border:1px solid #8cbbe1;border-radius:10px;font-size:14px;font-weight:800}
QComboBox,QLineEdit,QDateEdit{background:#fff;border:2px solid #a3c6e4;border-radius:9px;padding:9px;color:#10365b;min-height:22px}
QComboBox#toolbarSelect{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #187fbd,stop:1 #063661);color:white;font-weight:800;font-size:15px}
QComboBox QAbstractItemView{background:white;color:#102d50;selection-background-color:#b8dff9}
QPushButton#clearFilters{color:#123c83;background:#d6ebff;border-color:#658bbc}
QTableWidget{font-size:14px;background:#fff;alternate-background-color:#dceafb;gridline-color:#bfd5ec;selection-background-color:#86c5f3;selection-color:#06284b;border:2px solid #a7c8e5;border-radius:12px}
QTableWidget::item{padding:7px}
QHeaderView::section{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1779b4,stop:1 #063356);color:white;padding:8px;border:1px solid #3375a5;font-weight:bold;font-size:14px}
QScrollBar:vertical{background:#d8e8f8;width:14px}
QScrollBar::handle:vertical{background:#6d9ec4;border-radius:6px;min-height:24px}
QDialog{background:#eaf2fc;color:#102d50}
QStatusBar{background:#082d55;color:white;font-weight:bold}
QStatusBar QLabel{color:white;background:transparent;padding:4px}
QStatusBar::item{border:0}
""")
  self.search.textChanged.connect(self.apply_search)
  self.month_filter.currentIndexChanged.connect(self.apply_search)
  self.date_from.dateChanged.connect(self.apply_search)
  self.date_to.dateChanged.connect(self.apply_search)
  self.statusBar().setFixedHeight(36)
  self.mode.setCurrentText("Hyrjet")
  self.load()
  self.navigate("Hyrjet")
 def reset_date_range(self):
  year=int(self.year.currentText())
  for widget,date in ((self.date_from,QDate(year,1,1)),(self.date_to,QDate(year,12,31))):
   widget.blockSignals(True);widget.setDate(date);widget.blockSignals(False)
 def year_changed(self):
  self.reset_date_range();self.load()
 def add_record(self):
  mode=self.mode.currentText()
  if mode=="Anëtarësia":self.add_member()
  else:self.add_transaction(mode)
 def record_menu(self,point):
  index=self.table.indexAt(point)
  if index.isValid():
   self.table.selectRow(index.row())
  menu=QMenu(self)
  menu.addAction("Ndrysho",self.edit_record)
  menu.addAction("Dëftesë PDF",self.receipt_pdf)
  menu.exec(self.table.viewport().mapToGlobal(point))
 def edit_record(self):
  row=self.table.currentRow()
  if row<0:return
  item=self.table.item(row,0)
  record_id=item.data(Qt.UserRole)
  if not record_id or record_id>0:
   QMessageBox.information(self,"Burimi","Regjistrimet nga burimi përditësohen në tabelën origjinale dhe importohen nga Cilësimet.")
  elif self.mode.currentText()=="Anëtarësia":
   self.add_member(-record_id)
  else:
   self.add_transaction(self.mode.currentText(),-record_id)
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
 def add_member(self,rowid=None):
  dialog=QDialog(self);dialog.setWindowTitle("Anëtar i ri");form=QFormLayout(dialog)
  inputs=[]
  for label in ("ID","Emri","Mbiemri","Metoda (Cash/Bank)","Jan","Shk","Mar","Pri","Maj","Qer","Kor","Gush","Shta","Tet","Nën","Dhj"):
   field=QLineEdit();form.addRow(label,field);inputs.append(field)
  if rowid:
   row=db.execute("SELECT * FROM members WHERE rowid=?",(rowid,)).fetchone()
   for field,value in zip(inputs,row[1:]):field.setText(str(value or ""))
  save=QPushButton("Ruaj anëtarin");form.addRow(save)
  def commit():
   values=[x.text().strip() for x in inputs]
   if not all(values[:3]):QMessageBox.warning(dialog,"Kontroll","ID, emri dhe mbiemri janë të detyrueshëm.");return
   if rowid:
    db.execute("UPDATE members SET member_id=?,first_name=?,last_name=?,method=?,jan=?,feb=?,mar=?,apr=?,may=?,jun=?,jul=?,aug=?,sep=?,oct=?,nov=?,dec=? WHERE rowid=?",(*values,rowid))
   else:
    db.execute("INSERT INTO members VALUES ("+",".join(["?"]*17)+")",(int(self.year.currentText()),*values))
   db.commit();dialog.accept();self.mode.setCurrentText("Anëtarësia");self.load()
  save.clicked.connect(commit);dialog.exec()
 def add_transaction(self,kind,rowid=None):
  dialog=QDialog(self);dialog.setWindowTitle("Regjistro "+kind);form=QFormLayout(dialog)
  year=int(self.year.currentText())
  today=datetime.date.today()
  date=QLineEdit((today if today.year==year else datetime.date(year,1,1)).strftime("%d.%m.%Y"));date.setPlaceholderText("DD.MM.VVVV")
  description=QLineEdit();description.setPlaceholderText("Përshkrimi i transaksionit")
  method=QComboBox();method.addItems(["Cash","Bank","E paklasifikuar"])
  category=QComboBox();category.setEditable(True)
  categories=(["Anëtarësia","Donacion","Sadaka","Zekat","Fitër","Kurban","Aktivitete","Të ardhura të tjera"] if kind=="Hyrjet" else ["Qira","Rroga","Nebenkosten","Energji","Ujë","Mirëmbajtje","Pajisje","Aktivitete","Shpenzime të tjera"])
  category.addItems(categories+["Transfer i brendshëm","Gjendje fillestare"])
  for label,widget in (("Data",date),("Përshkrimi",description),("Mënyra e pagesës",method),("Lloji / Kategoria",category)):
   form.addRow(label,widget)
  amount=QDoubleSpinBox();amount.setMaximum(10000000);amount.setDecimals(2);amount.setSuffix(" €");form.addRow("Shuma",amount)
  if rowid:
   saved=db.execute("SELECT date,description,method,category,amount FROM finance WHERE rowid=?",(rowid,)).fetchone()
   date.setText(saved[0]);description.setText(saved[1]);method.setCurrentText(saved[2]);category.setCurrentText(saved[3])
   from ledger_totals import cents
   amount.setValue(cents(saved[4])/100)
  save=QPushButton("Ruaj regjistrimin");form.addRow(save)
  def commit():
   vals=[date.text().strip(),description.text().strip(),method.currentText(),category.currentText().strip()]
   try:parsed=datetime.datetime.strptime(vals[0],"%d.%m.%Y")
   except ValueError:QMessageBox.warning(dialog,"Data","Përdor DD.MM.VVVV");return
   if parsed.year!=year:QMessageBox.warning(dialog,"Data","Data duhet të jetë në vitin e zgjedhur.");return
   vals[0]=parsed.strftime("%d.%m.%Y")
   if not vals[1] or not vals[3] or amount.value()<=0:QMessageBox.warning(dialog,"Kontroll","Plotëso përshkrimin, kategorinë dhe shumën më të madhe se zero.");return
   if rowid:
    db.execute("UPDATE finance SET date=?,description=?,method=?,category=?,amount=? WHERE rowid=?",(*vals,f"{amount.value():.2f}",rowid))
   else:
    db.execute("INSERT INTO finance VALUES (?,?,?,?,?,?,?)",(year,kind,*vals,f"{amount.value():.2f}"))
   db.commit();dialog.accept();self.mode.setCurrentText(kind);self.load()
  save.clicked.connect(commit);dialog.exec()
 def reset_filters(self):
  self.reset_date_range();self.search.clear();self.month_filter.setCurrentIndex(0);self.apply_search()
 def apply_search(self,*args):
  needle=self.search.text().strip().casefold()
  start=self.date_from.date();end=self.date_to.date()
  year=int(self.year.currentText())
  date_active=(start,end)!=(QDate(year,1,1),QDate(year,12,31))
  month=self.month_filter.currentIndex()
  mode=self.mode.currentText()
  visible_count=0
  for i in range(self.table.rowCount()):
   cells=[self.table.item(i,j).text() if self.table.item(i,j) else "" for j in range(self.table.columnCount())]
   matches_text=not needle or any(needle in cell.casefold() for cell in cells)
   matches_date=True
   matches_month=month==0
   if mode!="Anëtarësia" and cells:
    date=QDate.fromString(cells[0],"dd.MM.yyyy")
    if not date.isValid():date=QDate.fromString(cells[0],Qt.ISODate)
    matches_date=not date_active or (date.isValid() and start<=date<=end)
    matches_month=not month or (date.isValid() and date.month()==month)
   if month and mode=="Anëtarësia":
    from seed_data import euros
    matches_month=len(cells)>month+3 and euros(cells[month+3])>0
   visible=matches_text and matches_date and matches_month
   self.table.setRowHidden(i,not visible)
   visible_count+=int(visible)
  source=""
  if mode!="Anëtarësia" and year==2026:
   has_sync=db.execute("SELECT 1 FROM sqlite_master WHERE name='source_sync'").fetchone()
   stamp=db.execute("SELECT synced_at FROM source_sync WHERE id=1").fetchone() if has_sync else None
   source=f" · Importuar {stamp[0].replace('T',' ')}" if stamp else " · Kopje e paketuar"
  self.statusBar().showMessage(f"{visible_count} nga {self.table.rowCount()} regjistrime · {mode} · {year}{source}")
  financial=mode!="Anëtarësia"
  noun={"Hyrjet":"hyrje","Daljet":"dalje","Anëtarësia":"anëtar"}[mode]
  self.add_button.setText(f"Shto {noun}")
  self.register_button.setText(f"Regjistro {noun}")
  self.filter_label.setText("Filtrimi i "+mode.lower())
  self.search.setPlaceholderText("Kërko përshkrim, kategori..." if financial else "Kërko emër, mbiemër...")
  for field in (self.date_from,self.date_to):field.setEnabled(financial)
  for card in self.stat_cards:card.setVisible(financial)
  if financial:
   visible_rows=[record for index,record in enumerate(self.ledger_rows) if not self.table.isRowHidden(index)]
   values=totals(visible_rows)
   numbers=[values[key] for key in ("cash","bank","other")]
   for label,card,value in zip((f"{noun.title()} Cash",f"{noun.title()} Bank","Të paklasifikuara",f"Totali · {mode}"),self.stat_cards,numbers+[sum(numbers)]):
    card.setText(f"{label}\n{value/100:,.2f} €")
   self.summary_label.setText(f"Lëvizje të përfshira: {values['count']} · Për rakordim / përjashtuar: {values['excluded']}")
  else:self.summary_label.setText(f"Anëtarësia {year} · {visible_count} regjistrime")
 def navigate(self,name):
  for key,button in self.nav_buttons.items():button.setChecked(key==name)
  self.dashboard.setVisible(name=="Ballina")
  if name in ("Anëtarësia","Hyrjet","Daljet"):
   self.mode.setCurrentText(name);self.reset_filters()
  elif name=="Buchhaltung":
   Buchhaltung(self,db,int(self.year.currentText())).exec()
  elif name=="Bilanci":
   self.show_balance()
  elif name=="Dëftesat":
   self.receipt_pdf()
  elif name=="Vërtetimi i pagesave vjetore":
   self.open_annual_payment_confirmation()
  elif name=="Sistemi i Hoxhës":
   self.open_imam_office()
  elif name in ("Hudbe & Derse","Rregullorja"):
   section="hudbe" if name=="Hudbe & Derse" else "reg"
   self.open_imam_office(section,lambda:self.open_documents(name))
  elif name=="Cilësimet":
   self.open_settings()
  elif name!="Ballina":
   self.open_documents(name)
 def open_imam_office(self,section="",archive=None):
  self.open_html_document("Sistemi i Hoxhës","sistemi_i_hoxhes.html",section,archive)

 def open_annual_payment_confirmation(self):
  self.open_html_document("Anlage 14","anlage14_jahreszahlungen.html")

 def open_html_document(self,title,filename,section="",archive=None):
  template=ASSETS.parent/"templates"/filename
  if not template.is_file():
   QMessageBox.warning(self,title,"HTML-ja mungon në paketën e programit.")
   return
  if not hasattr(self,"document_profile"):
   self.document_profile=QWebEngineProfile("XhamiaDocuments",QApplication.instance())
   self.document_profile.setPersistentStoragePath(str(ROOT/"web-documents"))
   self.document_profile.setCachePath(str(ROOT/"web-cache"))
  dialog=HtmlDocument(self,title,template,section,archive)
  dialog.exec()
  dialog.deleteLater()

 def open_settings(self):
  dialog=QDialog(self);dialog.setWindowTitle("Cilësimet dhe burimet zyrtare")
  layout=QVBoxLayout(dialog)
  layout.addWidget(QLabel(f"Databaza lokale\\n{database_path}"))
  for label,gid in TABS.items():
   button=QPushButton("Hap në Google Sheets · "+label)
   button.clicked.connect(lambda checked=False,tab=gid:QDesktopServices.openUrl(QUrl(f"{SHEET}/edit#gid={tab}")))
   layout.addWidget(button)
  download=QPushButton("Shkarko Excel nga Google Sheets")
  download.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(SHEET+"/export?format=xlsx")))
  layout.addWidget(download)
  def refresh_workbook():
   path,_=QFileDialog.getOpenFileName(dialog,"Zgjidh Excel-in e burimit","","Excel (*.xlsx)")
   if not path:return
   try:
    backup_path=import_workbook(db,path,ROOT);self.load()
    QMessageBox.information(dialog,"U importua",f"Burimi u përditësua. Kopja e sigurisë:\n{backup_path}")
   except Exception as exc:QMessageBox.critical(dialog,"Importi",str(exc))
  importer=QPushButton("Importo Excel të shkarkuar");importer.clicked.connect(refresh_workbook);layout.addWidget(importer)
  sync=QPushButton("Përditëso nga Google Sheets")
  layout.addWidget(sync)
  network=QNetworkAccessManager(dialog)
  def sync_workbook():
   sync.setEnabled(False);sync.setText("Po shkarkohet dokumenti origjinal…")
   request=QNetworkRequest(QUrl(SHEET+"/export?format=xlsx"));request.setTransferTimeout(25000)
   reply=network.get(request)
   def finished():
    try:
     if reply.error()!=QNetworkReply.NoError:raise ValueError(reply.errorString())
     data=bytes(reply.readAll())
     if not data.startswith(b"PK"):raise ValueError("Google kërkon hyrje. Shkarko Excel-in në shfletues dhe importoje.")
     with tempfile.TemporaryDirectory() as directory:
      path=Path(directory)/"finance.xlsx";path.write_bytes(data)
      backup_path=import_workbook(db,path,ROOT)
     self.load()
     QMessageBox.information(dialog,"U përditësua",f"Të dhënat zyrtare u ruajtën lokalisht. Kopja e sigurisë:\n{backup_path}")
    except Exception as exc:QMessageBox.critical(dialog,"Përditësimi",str(exc))
    finally:
     reply.deleteLater();sync.setEnabled(True);sync.setText("Përditëso nga Google Sheets")
   reply.finished.connect(finished)
  sync.clicked.connect(sync_workbook)
  def choose_photo():
   path,_=QFileDialog.getOpenFileName(dialog,"Zgjidh fotografinë origjinale të xhamisë","","Fotografi (*.jpg *.jpeg *.png)")
   if not path:return
   photo=QPixmap(path)
   if photo.isNull() or not photo.save(str(ROOT/"mosque_interior.jpg"),"JPEG",95):
    QMessageBox.warning(dialog,"Fotografia","Fotografia nuk u ruajt.");return
   self._render_hero()
  photo_button=QPushButton("Vendos fotografinë origjinale");photo_button.clicked.connect(choose_photo);layout.addWidget(photo_button)
  backup=QPushButton("Ruaj kopje sigurie");backup.clicked.connect(self.backup);layout.addWidget(backup)
  dialog.exec()
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
  def import_text():
   path,_=QFileDialog.getOpenFileName(dialog,"Importo dokument","","Tekst ose HTML (*.txt *.html *.htm)")
   if not path:return
   try:text=Path(path).read_text(encoding="utf-8-sig")
   except (OSError,UnicodeError) as exc:QMessageBox.warning(dialog,"Importi",str(exc));return
   new();title.setText(Path(path).stem)
   if Path(path).suffix.lower() in (".html",".htm"):body.setHtml(text)
   else:body.setPlainText(text)
  for label,callback in (("Dokument i ri",new),("Importo tekst / HTML",import_text),("Ruaj ndryshimet",save),("Eksporto PDF",export)):
   button=QPushButton(label);button.clicked.connect(callback);toolbar.addWidget(button)
  listing.itemClicked.connect(choose)
  refresh();dialog.exec()
 def load(self):
  y=int(self.year.currentText());mode=self.mode.currentText()
  if mode=="Anëtarësia":
   heads=["ID","Emri","Mbiemri","Bank","Jan","Shk","Mar","Pri","Maj","Qer","Kor","Gush","Shta","Tet","Nën","Dhj"]
   rows=db.execute("""SELECT m.source_row,m.member_id,m.first_name,m.last_name,m.bank,
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
   extra=db.execute("SELECT -rowid,member_id,first_name,last_name,method,jan,feb,mar,apr,may,jun,jul,aug,sep,oct,nov,dec FROM members WHERE year=?",(y,)).fetchall()
   ids=[row[0] for row in rows+extra]
   rows=[row[1:] for row in rows+extra]
  else:
   heads=["Data","Përshkrimi","Metoda","Kategoria","Shuma","Statusi"]
   self.ledger_rows=records(db,y,mode)
   ids=[row[6] for row in self.ledger_rows]
   rows=[(*record[:4],f"{record[4]/100:,.2f} €",exclusion(record) or "Përfshirë") for record in self.ledger_rows]
  self.table.verticalHeader().setVisible(mode!="Anëtarësia")
  self.table.setColumnCount(len(heads));self.table.setHorizontalHeaderLabels(heads);self.table.setRowCount(len(rows))
  for i,row in enumerate(rows):
   for j,val in enumerate(row):
    item=QTableWidgetItem(str(val or ""))
    if not j:item.setData(Qt.UserRole,ids[i])
    if mode!="Anëtarësia" and j==4:item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
    if mode!="Anëtarësia" and j==2:
     item.setForeground(QBrush(QColor("#167147" if val=="Cash" else "#0a56a3")))
    self.table.setItem(i,j,item)
  header=self.table.horizontalHeader()
  header.setMinimumSectionSize(38)
  header.setStretchLastSection(False)
  self.table.verticalHeader().setFixedWidth(43)
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
   for column,size in ((0,105),(2,88),(4,105),(5,125)):
    header.setSectionResizeMode(column,QHeaderView.Interactive)
    self.table.setColumnWidth(column,size)
   header.setSectionResizeMode(1,QHeaderView.Stretch)
  self.apply_search()
 def show_balance(self):
  y=int(self.year.currentText())
  try:
   values=summary(db,y)
   incoming=values["Hyrjet"];outgoing=values["Daljet"]
   cash=incoming["cash"]-outgoing["cash"]
   bank=incoming["bank"]-outgoing["bank"]
   total=cash+bank
   details=QDialog(self);details.setWindowTitle(f"Bilanci ndër vite — {y}");details.resize(850,560)
   layout=QVBoxLayout(details)
   title=QLabel(f"BILANCI VJETOR {y}");title.setAlignment(Qt.AlignCenter)
   title.setStyleSheet("font-size:24px;color:#e2c47c;font-weight:bold;padding:16px")
   layout.addWidget(title)
   grid=QTableWidget(4,4);grid.setEditTriggers(QAbstractItemView.NoEditTriggers)
   grid.setHorizontalHeaderLabels(["Llogaria","Hyrjet","Daljet","Diferenca"])
   for i,(label,inc,out) in enumerate((("Cash",incoming["cash"],outgoing["cash"]),("Bank",incoming["bank"],outgoing["bank"]),("Të paklasifikuara",incoming["other"],outgoing["other"]),("Gjithsej",sum(incoming[k] for k in ("cash","bank","other")),sum(outgoing[k] for k in ("cash","bank","other"))))):
    for j,value in enumerate((label,f"{inc/100:,.2f} €",f"{out/100:,.2f} €",f"{(inc-out)/100:,.2f} €")):
     grid.setItem(i,j,QTableWidgetItem(value))
   grid.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
   layout.addWidget(grid)
   notice=QLabel("Diferencat janë lëvizje të regjistruara, jo domosdoshmërisht gjendja reale e bankës.\\nGjendjet fillestare dhe rakordimet duhet të kontrollohen veçmas.")
   comparison=reconciliation(db,y)
   if comparison:
    audit=["Krahasimi me fletën Gjendja (vetëm rreshtat e burimit)"]
    for kind,(calculated,official) in comparison.items():
     audit.append(f"{kind}: klasifikuar {calculated/100:,.2f} € · fleta {official/100:,.2f} € · diferenca {(calculated-official)/100:+,.2f} €")
    audit_label=QLabel("\n".join(audit));audit_label.setWordWrap(True);layout.addWidget(audit_label)
   notice.setWordWrap(True);layout.addWidget(notice)
   buttons=QHBoxLayout();layout.addLayout(buttons)
   export=QPushButton("Eksporto raportin PDF");export.clicked.connect(self.financial_pdf);buttons.addWidget(export)
   for label in ("Bilanci aktual · rakordimi","Bilanci ndër vite","Gjendja 2026"):
    button=QPushButton(label);button.clicked.connect(lambda checked=False,n=label:self.show_source_balance(n));buttons.addWidget(button)
   close=QPushButton("Mbyll");close.clicked.connect(details.accept);buttons.addWidget(close)
   details.exec()
  except Exception as exc:QMessageBox.critical(self,"Bilanci",str(exc))
 def show_source_balance(self,label):
  tab={"Bilanci aktual · rakordimi":"Rakordimi i saktë 2026","Bilanci ndër vite":"BILANCI MASTER","Gjendja 2026":"Gjendja"}[label]
  if not db.execute("SELECT 1 FROM sqlite_master WHERE name='source_balance'").fetchone():
   QDesktopServices.openUrl(QUrl(f"{SHEET}/edit#gid={TABS[label]}"));return
  rows=db.execute("SELECT row_num,col_num,value FROM source_balance WHERE tab=?",(tab,)).fetchall()
  if not rows:return
  dialog=QDialog(self);dialog.setWindowTitle(label);dialog.resize(1120,600)
  layout=QVBoxLayout(dialog)
  stamp=db.execute("SELECT synced_at FROM source_sync WHERE id=1").fetchone()[0]
  layout.addWidget(QLabel(f"Kopja lokale nga Google Sheets · {stamp}"))
  grid=QTableWidget(max(row for row,_,_ in rows),max(column for _,column,_ in rows))
  grid.setEditTriggers(QAbstractItemView.NoEditTriggers);grid.setAlternatingRowColors(True)
  for row,column,value in rows:grid.setItem(row-1,column-1,QTableWidgetItem(value))
  grid.resizeColumnsToContents();layout.addWidget(grid)
  source=QPushButton("Hap fletën aktuale në Google Sheets")
  source.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(f"{SHEET}/edit#gid={TABS[label]}")))
  layout.addWidget(source);dialog.exec()
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
  if exclusion(self.ledger_rows[i]):
   QMessageBox.warning(self,"Dëftesa","Ky rresht është përjashtuar nga hyrjet.");return
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
   if Path(target).resolve()==database_path.resolve():raise ValueError("Zgjidh një skedar tjetër për kopjen.")
   backup_database(db,target)
   QMessageBox.information(self,"Backup","Kopja e sigurisë u ruajt.")
  except Exception as e:QMessageBox.critical(self,"Backup",str(e))
 def import_csv(self):
  import csv
  p,_=QFileDialog.getOpenFileName(self,"Zgjidh CSV","","CSV (*.csv)")
  if not p:return
  try:
   with open(p,encoding="utf-8-sig",newline="") as f:rows=list(csv.reader(f))
   y=int(self.year.currentText());mode=self.mode.currentText()
   with db:
    for row in rows[1:]:
     if not any(row):continue
     if mode=="Anëtarësia" and len(row)>=16:
      db.execute("INSERT INTO members VALUES ("+",".join(["?"]*17)+")",[y]+row[:16])
     elif mode!="Anëtarësia" and len(row)>=5:
      date=datetime.datetime.strptime(row[0].strip(),"%d.%m.%Y")
      if date.year!=y:raise ValueError(f"Data {row[0]} nuk i përket vitit {y}.")
      db.execute("INSERT INTO finance VALUES (?,?,?,?,?,?,?)",[y,mode,date.strftime("%d.%m.%Y")]+row[1:5])
     else:raise ValueError("Kolonat e CSV-së nuk përputhen me rubrikën e hapur.")
   self.load()
  except Exception as e:QMessageBox.critical(self,"Importi",str(e))
 def pdf(self):
  p,_=QFileDialog.getSaveFileName(self,"Ruaj PDF",f"{self.mode.currentText()}_{self.year.currentText()}.pdf","PDF (*.pdf)")
  if not p:return
  try:
   data=[[self.table.horizontalHeaderItem(j).text() for j in range(self.table.columnCount())]]
   for i in range(self.table.rowCount()):
    if self.table.isRowHidden(i):continue
    data.append([(self.table.item(i,j).text() if self.table.item(i,j) else "") for j in range(self.table.columnCount())])
   doc=SimpleDocTemplate(p,pagesize=landscape(A4));styles=getSampleStyleSheet()
   t=Table(data,repeatRows=1,hAlign="LEFT");t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#193c58")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTSIZE",(0,0),(-1,-1),6),("GRID",(0,0),(-1,-1),.25,colors.grey)]))
   doc.build([Paragraph("Xhamia Frankenthal - "+self.mode.currentText()+" "+self.year.currentText(),styles["Heading1"]),t])
  except Exception as e:QMessageBox.critical(self,"PDF",str(e))
if __name__=="__main__":
 app=QApplication(sys.argv)
 app.setWindowIcon(QIcon(mosque_logo()))
 login=Login()
 if "--smoke-test" in sys.argv:
  login.show();app.processEvents()
  assert login.isVisible() and login.p.echoMode()==QLineEdit.Password
  login.check();assert login.error.text()
  login.hide()
  win=Main();win.show();app.processEvents()
  assert not mosque_logo().isNull() and not login.windowIcon().isNull()
  assert not win.hero.photo.isNull() and not win.hero.emblem.pixmap().isNull()
  assert win.table.rowCount()>0 and len(win.nav_buttons)==15
  win.search.setText("no-match-6ddba")
  assert all(win.table.isRowHidden(row) for row in range(win.table.rowCount()))
  win.reset_filters()
  assert not win.table.isRowHidden(0)
  win.month_filter.setCurrentIndex(1)
  assert any(win.table.isRowHidden(row) for row in range(win.table.rowCount()))
  win.reset_filters()
  win.resize(1080,690);app.processEvents()
  assert win.table.isVisible() and win.table.height()>=95
  screenshot=os.getenv("XHAMIA_SMOKE_SCREENSHOT")
  if screenshot:
   win.setFixedSize(1536,830);app.processEvents()
   assert win.size()==QSize(1536,830)
   assert win.grab().save(screenshot)

  win.navigate("Daljet")
  assert win.table.rowCount()>0 and win.stat_cards[3].isVisible()
  win.navigate("Anëtarësia")
  assert win.table.rowCount()>0
  opened_dialogs=[]
  def close_balance():
   modal=app.activeModalWidget()
   if modal:
    opened_dialogs.append(modal.windowTitle())
    modal.accept()
  QTimer.singleShot(50,close_balance)
  win.navigate("Bilanci")
  assert opened_dialogs==["Bilanci ndër vite — 2026"]
  books=Buchhaltung(win,db,2025)
  assert books.book.rowCount()>0
  books.year.setCurrentText("2026")
  assert books.book.rowCount()>0 and books.docs.rowCount()==0
  from unittest.mock import patch
  for section,selector in (("docs","[onclick='openNikah()']"),("hudbe",".nav button.active[onclick^=\"show('hudbe'\"]"),("","#tax")):
   observed=[]
   def inspect_document(dialog):
    def loaded(ok):
     if not ok:
      dialog.reject()
      return
     expression=f"Boolean(document.querySelector({selector!r}))"
     if not section:expression+=" && typeof render === 'function' && document.getElementById('tax').value === '27/659/06083'"
     dialog.view.page().runJavaScript(expression, lambda result:(observed.append(result),dialog.accept()))
    dialog.view.loadFinished.connect(loaded)
    QTimer.singleShot(15000,dialog,dialog.reject)
    return QDialog.exec(dialog)
   with patch.object(HtmlDocument,"exec",inspect_document):
    if section:win.open_imam_office(section)
    else:win.open_annual_payment_confirmation()
   assert observed==[True], (section,observed)
   app.processEvents()
  sys.exit(0)
 if login.exec()==QDialog.Accepted:
  win=Main();win.show();sys.exit(app.exec())
