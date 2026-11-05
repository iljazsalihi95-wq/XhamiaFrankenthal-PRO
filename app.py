import sys, sqlite3, os, shutil, datetime, hashlib, hmac, urllib.request, json
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QComboBox,QFileDialog,QMessageBox,QLineEdit,QDialog,QFormLayout,QFrame,QDoubleSpinBox
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QPixmap, QIcon
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
 """Cache the mosque's real logo for native Qt controls; no HTML rendering."""
 cache=ROOT/"mosque_logo.png"
 if not cache.exists():
  try:
   with urllib.request.urlopen(LOGO_URL,timeout=3) as response:
    data=response.read(2_000_000)
   if data.startswith(b"\\x89PNG") or data.startswith(b"\\xff\\xd8"):
    cache.write_bytes(data)
  except Exception:pass
 return QPixmap(str(cache)) if cache.exists() else QPixmap()

class Login(QDialog):
 def __init__(self):
  super().__init__();self.setWindowTitle("Xhamia Frankenthal PRO - Hyrja")
  self.setMinimumWidth(440)
  f=QFormLayout(self)
  emblem=QLabel();emblem.setAlignment(Qt.AlignCenter)
  picture=mosque_logo()
  if not picture.isNull():emblem.setPixmap(picture.scaled(150,150,Qt.KeepAspectRatio,Qt.SmoothTransformation));self.setWindowIcon(QIcon(picture))
  else:emblem.setText("XHAMIA FRANKENTHAL")
  f.addRow(emblem)
  caption=QLabel("SISTEMI I ADMINISTRIMIT  •  WINDOWS");caption.setAlignment(Qt.AlignCenter);f.addRow(caption)
  self.u=QLineEdit();self.p=QLineEdit();self.p.setEchoMode(QLineEdit.Password);f.addRow("Përdoruesi",self.u);f.addRow("Fjalëkalimi",self.p)
  b=QPushButton("Hyr");b.clicked.connect(self.check);f.addRow(b)
 def check(self):
  if self.u.text()=="XhamiaFrankenthal" and hmac.compare_digest(hashlib.sha256(self.p.text().encode()).hexdigest(),"4590c57bbe71fba3b0b4586e439d54f410eca68a7e1e17ba8f0f16b129d02b6f"):self.accept()
  else:QMessageBox.warning(self,"Gabim","Kredencialet nuk përputhen")
class Main(QMainWindow):
 def __init__(self):
  super().__init__();self.setWindowTitle("Xhamia Frankenthal PRO");self.resize(1200,760)
  pic=mosque_logo()
  if not pic.isNull():self.setWindowIcon(QIcon(pic))
  w=QWidget();self.setCentralWidget(w);v=QVBoxLayout(w)
  v.setContentsMargins(22,16,22,18);v.setSpacing(14)
  title=QLabel("XHAMIA FRANKENTHAL PRO");title.setAlignment(Qt.AlignCenter);title.setStyleSheet("font-size:26px;font-weight:bold;color:#d5b46b");v.addWidget(title)
  body=QHBoxLayout();v.addLayout(body,1)
  sidebar=QFrame();sidebar.setObjectName("sidebar");sidebar.setFixedWidth(210)
  nav=QVBoxLayout(sidebar);nav.setContentsMargins(12,20,12,16);nav.setSpacing(10)
  logo=QLabel();logo.setAlignment(Qt.AlignCenter);logo.setMinimumHeight(118)
  if not pic.isNull():logo.setPixmap(pic.scaled(112,112,Qt.KeepAspectRatio,Qt.SmoothTransformation))
  else:logo.setText("IVF")
  nav.addWidget(logo)
  brand=QLabel("ISLAMISCHER VEREIN\\nFRANKENTHAL e.V.");brand.setWordWrap(True);brand.setAlignment(Qt.AlignCenter);brand.setStyleSheet("color:#e2c47c;font-weight:bold;font-size:13px");nav.addWidget(brand)
  for name in ("Ballina","Anëtarësia","Hyrjet","Daljet","Bilanci","Dëftesat","Hudbe & Derse"):
   button=QPushButton(name);button.setMinimumHeight(42)
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
  self.dashboard.setAlignment(Qt.AlignCenter);self.dashboard.setMinimumHeight(92);self.dashboard.setStyleSheet("font-size:20px;font-weight:600;color:#e2c47c;padding:20px;border:1px solid #9e824c;border-radius:15px;background:#10313b")
  work.addWidget(self.dashboard)
  actions=QHBoxLayout();work.addLayout(actions)
  for label,callback in (("Shto anëtar",self.add_member),("Bart anëtarët në vitin pasues",self.rollover_members),("Regjistro hyrje",lambda:self.add_transaction("Hyrjet")),("Regjistro dalje",lambda:self.add_transaction("Daljet"))):
   btn=QPushButton(label);btn.clicked.connect(callback);actions.addWidget(btn)
  self.summary_label=QLabel("Raport nga të dhënat e importuara — pa rakordim bankar");work.addWidget(self.summary_label)
  self.table=QTableWidget();self.table.setAlternatingRowColors(True);self.table.setMinimumHeight(390);self.table.verticalHeader().setDefaultSectionSize(34);self.table.verticalHeader().setVisible(False);self.table.setWordWrap(False);work.addWidget(self.table,3);self.mode.currentIndexChanged.connect(self.load);self.year.currentIndexChanged.connect(self.load)
  self.setStyleSheet("""
QMainWindow,QWidget{background:#081d28;color:#f2f7f5;font-family:'Segoe UI';font-size:13px}
QFrame#sidebar{background:#0e3039;border:1px solid #a28b54;border-radius:16px} QPushButton{background:#174c55;border:1px solid #b69b57;border-radius:8px;padding:10px;color:#f6e7b5;font-weight:600}
QPushButton:hover{background:#246a70}
QComboBox,QLineEdit{background:#143642;border:1px solid #42616a;border-radius:7px;padding:8px;color:white}
QTableWidget{font-size:14px;background:#102c38;alternate-background-color:#173843;gridline-color:#36535b;selection-background-color:#276b6e}
QHeaderView::section{background:#18515a;color:#f3dfab;padding:11px;border:0;font-weight:bold}
QScrollBar{background:#102c38}\nQDialog{background:#081d28;color:#f2f7f5}
""")
  self.search.textChanged.connect(self.apply_search)
  self.month_filter.currentIndexChanged.connect(self.apply_search)
  self.date_filter.textChanged.connect(self.apply_search)
  self.load()
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
