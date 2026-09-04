import json, os, secrets, sqlite3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).parent; DB=ROOT/'mindmatch.db'
def connect():
    db=sqlite3.connect(DB); db.row_factory=sqlite3.Row; return db
def setup():
    with connect() as db: db.executescript('CREATE TABLE IF NOT EXISTS quizzes(id TEXT PRIMARY KEY, creator_key TEXT NOT NULL, creator_name TEXT NOT NULL, questions TEXT NOT NULL, answers TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS responses(id TEXT PRIMARY KEY, quiz_id TEXT NOT NULL, respondent_name TEXT NOT NULL, answers TEXT NOT NULL, score INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);')
class App(SimpleHTTPRequestHandler):
    def json(self,status,data):
        b=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',len(b)); self.end_headers(); self.wfile.write(b)
    def body(self): return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
    def new_id(self,table):
        while True:
            value=secrets.token_urlsafe(6).replace('-','').replace('_','')[:8]
            with connect() as db:
                if not db.execute(f'SELECT 1 FROM {table} WHERE id=?',(value,)).fetchone(): return value
    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path
        if not path.startswith('/api/quizzes/'): return super().do_GET()
        bits=path.split('/'); qid=bits[3]
        with connect() as db: q=db.execute('SELECT * FROM quizzes WHERE id=?',(qid,)).fetchone()
        if not q:return self.json(404,{'error':'Quiz not found.'})
        questions=json.loads(q['questions'])
        if len(bits)>4 and bits[4]=='results':
            if parse_qs(parsed.query).get('key',[''])[0]!=q['creator_key']:return self.json(403,{'error':'That creator link is not valid.'})
            with connect() as db: rows=db.execute('SELECT respondent_name,score,created_at FROM responses WHERE quiz_id=? ORDER BY created_at DESC',(qid,)).fetchall()
            return self.json(200,{'creatorName':q['creator_name'],'questionCount':len(questions),'responses':[{'respondentName':r['respondent_name'],'score':r['score'],'createdAt':r['created_at']+'Z'} for r in rows]})
        self.json(200,{'id':qid,'creatorName':q['creator_name'],'questions':questions})
    def do_POST(self):
        path=urlparse(self.path).path
        try:
            data=self.body()
            if path=='/api/quizzes':
                name=str(data.get('creatorName','')).strip(); questions=data.get('questions'); answers=data.get('answers')
                if not name or not isinstance(questions,list) or not questions or len(questions)>30 or not isinstance(answers,list) or len(answers)!=len(questions):raise ValueError('Quiz details are incomplete.')
                clean=[]
                for i,q in enumerate(questions):
                    text=str(q.get('text','')).strip(); options=q.get('options',[])
                    if not text or not isinstance(options,list) or len(options)!=4 or any(not str(x).strip() for x in options) or not isinstance(answers[i],int) or answers[i] not in range(4):raise ValueError('Each question needs four answers and one correct choice.')
                    clean.append({'category':str(q.get('category','Your quiz'))[:40],'text':text[:220],'options':[str(x).strip()[:100] for x in options]})
                qid=self.new_id('quizzes'); key=secrets.token_urlsafe(24)
                with connect() as db:db.execute('INSERT INTO quizzes(id,creator_key,creator_name,questions,answers) VALUES(?,?,?,?,?)',(qid,key,name[:30],json.dumps(clean),json.dumps(answers)))
                return self.json(201,{'id':qid,'creatorKey':key})
            if path.startswith('/api/quizzes/') and path.endswith('/responses'):
                qid=path.split('/')[3]; name=str(data.get('respondentName','')).strip(); given=data.get('answers')
                with connect() as db:q=db.execute('SELECT answers FROM quizzes WHERE id=?',(qid,)).fetchone()
                if not q:return self.json(404,{'error':'Quiz not found.'})
                correct=json.loads(q['answers'])
                if not name or not isinstance(given,list) or len(given)!=len(correct) or any(not isinstance(x,int) or x not in range(4) for x in given):raise ValueError('Answers are incomplete.')
                score=sum(a==b for a,b in zip(given,correct)); rid=self.new_id('responses')
                with connect() as db:db.execute('INSERT INTO responses(id,quiz_id,respondent_name,answers,score) VALUES(?,?,?,?,?)',(rid,qid,name[:30],json.dumps(given),score))
                return self.json(201,{'id':rid,'respondentName':name[:30],'answers':given,'correctAnswers':correct,'score':score})
            self.json(404,{'error':'Not found.'})
        except (ValueError,json.JSONDecodeError) as e:self.json(400,{'error':str(e)})
        except Exception:self.json(500,{'error':'Server error.'})
if __name__=='__main__':
    host=os.environ.get('HOST','127.0.0.1'); port=int(os.environ.get('PORT','8000'))
    setup();print(f'MindMatch running at http://{host}:{port}');ThreadingHTTPServer((host,port),App).serve_forever()
