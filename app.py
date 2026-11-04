import sys, sqlite3, os, shutil, datetime, hashlib, hmac
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QComboBox,QFileDialog,QMessageBox,QLineEdit,QDialog,QFormLayout
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from seed_data import seed
from finance_reports import summary, report
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
class Login(QDialog):
 def __init__(self):
  super().__init__();self.setWindowTitle("Xhamia Frankenthal PRO - Hyrja")
  f=QFormLayout(self);self.u=QLineEdit();self.p=QLineEdit();self.p.setEchoMode(QLineEdit.Password);f.addRow("Përdoruesi",self.u);f.addRow("Fjalëkalimi",self.p)
  b=QPushButton("Hyr");b.clicked.connect(self.check);f.addRow(b)
 def check(self):
  if self.u.text()=="XhamiaFrankenthal" and hmac.compare_digest(hashlib.sha256(self.p.text().encode()).hexdigest(),"4590c57bbe71fba3b0b4586e439d54f410eca68a7e1e17ba8f0f16b129d02b6f"):self.accept()
  else:QMessageBox.warning(self,"Gabim","Kredencialet nuk përputhen")
class Main(QMainWindow):
 def __init__(self):
  super().__init__();self.setWindowTitle("Xhamia Frankenthal PRO");self.resize(1200,760)
  w=QWidget();self.setCentralWidget(w);v=QVBoxLayout(w)
  title=QLabel("XHAMIA FRANKENTHAL PRO");title.setAlignment(Qt.AlignCenter);title.setStyleSheet("font-size:26px;font-weight:bold;color:#d5b46b");v.addWidget(title)
  bar=QHBoxLayout();v.addLayout(bar)
  self.mode=QComboBox();self.mode.addItems(["Anëtarësia","Hyrjet","Daljet"]);bar.addWidget(self.mode)
  self.year=QComboBox();self.year.addItems([str(x) for x in range(2015,2036)]);self.year.setCurrentText("2026");bar.addWidget(self.year)
  for label,func in [("Importo CSV",self.import_csv),("Eksporto PDF",self.pdf),("Backup",self.backup),("Raport financiar A4",self.financial_pdf),("Rifresko",self.load)]:
   b=QPushButton(label);b.clicked.connect(func);bar.addWidget(b)
  self.web=QWebEngineView();self.web.setMinimumHeight(300);self.web.load(QUrl.fromLocalFile(str(Path(getattr(sys,"_MEIPASS",Path(__file__).parent))/"assets"/"ballina_xhamia.html")))
  v.addWidget(self.web)
  toggle=QPushButton("Shfaq / fshih ballinën origjinale");toggle.clicked.connect(lambda:self.web.setVisible(not self.web.isVisible()));v.addWidget(toggle)
  self.summary_label=QLabel("Raport nga të dhënat e importuara — pa rakordim bankar");v.addWidget(self.summary_label)
  self.table=QTableWidget();self.table.setAlternatingRowColors(True);v.addWidget(self.table);self.mode.currentIndexChanged.connect(self.load);self.year.currentIndexChanged.connect(self.load)
  self.setStyleSheet("""
QMainWindow,QWidget{background:#081d28;color:#f2f7f5;font-family:'Segoe UI';font-size:13px}
QPushButton{background:#174c55;border:1px solid #b69b57;border-radius:8px;padding:10px;color:#f6e7b5;font-weight:600}
QPushButton:hover{background:#246a70}
QComboBox,QLineEdit{background:#143642;border:1px solid #42616a;border-radius:7px;padding:8px;color:white}
QTableWidget{background:#102c38;alternate-background-color:#173843;gridline-color:#36535b;selection-background-color:#276b6e}
QHeaderView::section{background:#18515a;color:#f3dfab;padding:8px;border:0}
QScrollBar{background:#102c38}
""")
  self.load()
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
  else:
   heads=["Data","Përshkrimi","Cash/Bank","Kategoria","Shuma"]
   sheet=mode if y==2026 else f"{mode} {y}"
   rows=db.execute("SELECT date,description,account,category,printf('%.2f €',amount_cents/100.0) FROM source_finance WHERE source_sheet=? ORDER BY source_row",(sheet,)).fetchall()
  self.table.setColumnCount(len(heads));self.table.setHorizontalHeaderLabels(heads);self.table.setRowCount(len(rows))
  for i,row in enumerate(rows):
   for j,val in enumerate(row):self.table.setItem(i,j,QTableWidgetItem(str(val or "")))
  self.table.resizeColumnsToContents()
  self.statusBar().showMessage(f"{len(rows)} regjistrime · {mode} · {y}")
  if mode!="Anëtarësia":
   totals=summary(db,y)
   d=totals[mode]
   self.summary_label.setText(f"{mode} {y}: Cash {d['cash']/100:,.2f} € | Bank {d['bank']/100:,.2f} € | Të paklasifikuara {d['other']/100:,.2f} € | Përjashtuar {d['excluded']} rreshta")
  else:self.summary_label.setText(f"Anëtarësia {y}: {len(rows)} rreshta nga burimi zyrtar")
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
