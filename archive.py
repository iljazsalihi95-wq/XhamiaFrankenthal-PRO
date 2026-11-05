"""Native Windows archive for mosque sermons, lessons and documents."""
import sqlite3, shutil, datetime
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,
 QPushButton,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QTextBrowser,
 QLabel,QSplitter,QHeaderView)

def open_archive(parent, root):
    root=Path(root)
    storage=root/"arkiva"
    storage.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(root/"xhamia.db")
    con.execute("""CREATE TABLE IF NOT EXISTS archive_items(
      id INTEGER PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
      date TEXT, filename TEXT NOT NULL UNIQUE)""")
    con.commit()
    dlg=QDialog(parent)
    dlg.setWindowTitle("Arkiva e Xhamisë — Hudbe, Derse dhe Dokumente")
    dlg.resize(1040,700)
    layout=QVBoxLayout(dlg)
    layout.addWidget(QLabel("ARKIVA E XHAMISË  •  Hudbe / Derse / Dokumente"))
    tools=QHBoxLayout();layout.addLayout(tools)
    query=QLineEdit();query.setPlaceholderText("Kërko titullin ose datën…");tools.addWidget(query)
    kind=QComboBox();kind.addItems(["Të gjitha","Hudbe","Ders","Dokument"]);tools.addWidget(kind)
    add=QPushButton("Importo dokument");tools.addWidget(add)
    splitter=QSplitter(Qt.Horizontal);layout.addWidget(splitter,1)
    table=QTableWidget(0,3);table.setHorizontalHeaderLabels(["Data","Lloji","Titulli"])
    table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)
    table.setSelectionBehavior(QTableWidget.SelectRows);table.setEditTriggers(QTableWidget.NoEditTriggers)
    splitter.addWidget(table)
    viewer=QTextBrowser();viewer.setOpenExternalLinks(False);splitter.addWidget(viewer)
    splitter.setSizes([410,620])
    bottom=QHBoxLayout();layout.addLayout(bottom)
    open_btn=QPushButton("Hap dokumentin");bottom.addWidget(open_btn)
    delete=QPushButton("Hiq nga arkiva");bottom.addWidget(delete)
    bottom.addStretch()
    close=QPushButton("Mbyll");close.clicked.connect(dlg.accept);bottom.addWidget(close)
    shown=[]
    def refresh():
        nonlocal shown
        needle=query.text().casefold().strip()
        category=kind.currentText()
        shown=[row for row in con.execute("SELECT id,kind,title,date,filename FROM archive_items ORDER BY date DESC,id DESC")
               if (category=="Të gjitha" or row[1]==category) and
                  (not needle or needle in (row[2]+" "+(row[3] or "")).casefold())]
        table.setRowCount(len(shown))
        for i,row in enumerate(shown):
            for j,val in enumerate((row[3],row[1],row[2])):
                table.setItem(i,j,QTableWidgetItem(str(val or "")))
        viewer.clear()
    def selected():
        i=table.currentRow()
        return shown[i] if 0<=i<len(shown) else None
    def preview():
        item=selected()
        if not item:return
        path=storage/item[4]
        if not path.is_file():
            viewer.setPlainText("Skedari mungon në arkiv.");return
        if path.suffix.lower() in (".txt",".html",".htm"):
            data=path.read_text(encoding="utf-8",errors="replace")
            if path.suffix.lower() in (".html",".htm"):viewer.setHtml(data)
            else:viewer.setPlainText(data)
        else:viewer.setPlainText("Dokumenti PDF ose Word hapet me programin përkatës. Kliko 'Hap dokumentin'.")
    def import_file():
        paths,_=QFileDialog.getOpenFileNames(dlg,"Zgjidh hudbet, dersët ose dokumentet","","Dokumente (*.html *.htm *.txt *.pdf *.docx)")
        if not paths:return
        category=kind.currentText()
        if category=="Të gjitha":category="Hudbe"
        count=0
        for source in paths:
            p=Path(source)
            dest=storage/p.name
            if dest.exists():
                n=1
                while (storage/(p.stem+"_"+str(n)+p.suffix)).exists():n+=1
                dest=storage/(p.stem+"_"+str(n)+p.suffix)
            try:
                shutil.copy2(p,dest)
                con.execute("INSERT INTO archive_items(kind,title,date,filename) VALUES(?,?,?,?)",
                    (category,p.stem,datetime.date.today().isoformat(),dest.name))
                count+=1
            except Exception as exc:QMessageBox.warning(dlg,"Importimi",str(exc))
        con.commit();refresh()
        QMessageBox.information(dlg,"Arkiva",f"U importuan {count} dokumente. Ruajtja është lokale.")
    def open_file():
        item=selected()
        if item:QDesktopServices.openUrl(QUrl.fromLocalFile(str((storage/item[4]).resolve())))
    def remove():
        item=selected()
        if not item:return
        if QMessageBox.question(dlg,"Konfirmim","Ta heqim këtë dokument nga arkiva?")==QMessageBox.Yes:
            con.execute("DELETE FROM archive_items WHERE id=?",(item[0],));con.commit();refresh()
    add.clicked.connect(import_file);query.textChanged.connect(refresh);kind.currentTextChanged.connect(refresh)
    table.itemSelectionChanged.connect(preview);open_btn.clicked.connect(open_file);delete.clicked.connect(remove)
    refresh();dlg.exec();con.close()
