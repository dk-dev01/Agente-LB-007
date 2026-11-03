"""Agente visual experimental para Maze: Path of Light (Windows)."""
from __future__ import annotations

import json
import math
import threading
import time
import platform
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path

try:
    import cv2
    import numpy as np
    import pyautogui
    from pynput import keyboard
except ModuleNotFoundError as exc:
    missing = exc.name or "pacote desconhecido"
    print(f"Dependência ausente: {missing}")
    print("No PowerShell, instale os pacotes com:")
    print("  python -m pip install -r requirements.txt")
    print("Execute o comando na pasta outputs onde estão maze_agent.py e requirements.txt.")
    raise SystemExit(1) from exc

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "maze_memoria.jsonl"
SCALE = 4
DATA_ROOT = ROOT / "dataset"
CONFIG_PATH = ROOT / "maze_config.json"
DEFAULT_CONFIG = {"grid_scale_px": 4, "key_hold_seconds": 0.45, "observation_delay_seconds": 0.45,
                  "movement_threshold_px": 3, "target_radius_px": 240, "input_backend": "pynput"}


def load_config():
    config=DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try: config.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError,json.JSONDecodeError) as exc: print(f"Aviso: configuração ignorada: {exc}")
    for key in DEFAULT_CONFIG:
        config[key]=type(DEFAULT_CONFIG[key])(config[key])
    return config


def select_rect(title: str):
    """Seleciona na tela e confirma mostrando somente o recorte escolhido."""
    screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
    print(title)
    while True:
        rect = cv2.selectROI("1. Arraste o retangulo; ENTER confirma", screen, fromCenter=False, showCrosshair=True)
        cv2.destroyAllWindows()
        x,y,w,h = map(int,rect)
        if w < 80 or h < 80: raise RuntimeError("Seleção cancelada ou pequena demais.")
        crop=screen[y:y+h,x:x+w].copy()
        if crop.size == 0: raise RuntimeError("A seleção ficou fora da captura. Selecione novamente.")
        scale=min(1.0,1100/crop.shape[1],680/crop.shape[0])
        preview=cv2.resize(crop,(round(crop.shape[1]*scale),round(crop.shape[0]*scale)),interpolation=cv2.INTER_AREA) if scale<1 else crop
        cv2.namedWindow("2. Somente a area selecionada",cv2.WINDOW_AUTOSIZE)
        cv2.imshow("2. Somente a area selecionada",preview)
        print("Prévia do recorte: ENTER confirma; R refaz a seleção; ESC cancela.")
        key=cv2.waitKey(0)&0xff
        cv2.destroyAllWindows()
        if key in (ord('r'),ord('R')): continue
        if key==27: raise RuntimeError("Seleção cancelada.")
        return x,y,w,h


def pick_points(board):
    """Cliques para indicar os centros aproximados da bola e do portal."""
    height,width=board.shape[:2]
    scale=min(1.0,1000/width,650/height)
    display=cv2.resize(board,(max(1,round(width*scale)),max(1,round(height*scale))),interpolation=cv2.INTER_AREA) if scale<1 else board.copy()
    panel=72
    preview=np.zeros((display.shape[0]+panel,display.shape[1],3),dtype=np.uint8)
    preview[panel:]=display
    cv2.putText(preview,"Bola e portal precisam estar visiveis neste recorte",(12,25),cv2.FONT_HERSHEY_SIMPLEX,0.62,(0,255,255),2,cv2.LINE_AA)
    cv2.putText(preview,"Clique BOLA, depois PORTAL | C refaz cliques | R refaz recorte",(12,53),cv2.FONT_HERSHEY_SIMPLEX,0.52,(255,255,255),2,cv2.LINE_AA)
    points = []
    def click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
            if y < panel: return
            points.append((min(width-1,int(x/scale)),min(height-1,int((y-panel)/scale))))
            cv2.circle(preview, (x,y), 9, (0,255,255) if len(points)==1 else (255,255,255), 2)
            cv2.imshow("Calibracao", preview)
    cv2.namedWindow("Calibracao", cv2.WINDOW_AUTOSIZE)
    cv2.imshow("Calibracao", preview)
    cv2.setMouseCallback("Calibracao", click)
    print("A bola e o portal precisam aparecer no recorte. Clique BOLA, depois PORTAL; R refaz o recorte; ESC cancela.")
    while True:
        key=cv2.waitKey(30)&0xff
        if key in (ord('r'),ord('R')):
            cv2.destroyWindow("Calibracao"); return None
        if key in (ord('c'),ord('C')):
            points.clear()
            preview[panel:]=display
            cv2.imshow("Calibracao",preview)
        if len(points)==2:
            gray=cv2.cvtColor(board,cv2.COLOR_BGR2GRAY)
            visible=[]
            for point in points:
                px,py=point; patch=gray[max(0,py-30):min(height,py+31),max(0,px-30):min(width,px+31)]
                visible.append(bool(patch.size and np.count_nonzero(patch>=175)>=8))
            if not all(visible):
                print("Nao detectei brilho suficiente perto dos pontos. Pressione C para clicar de novo ou R para refazer o recorte.")
                points.clear(); preview[panel:]=display; cv2.imshow("Calibracao",preview)
                continue
            break
        if key==27:
            cv2.destroyWindow("Calibracao"); raise RuntimeError("Calibracao cancelada.")
    cv2.destroyWindow("Calibracao")
    return points


def capture(rect):
    x,y,w,h = rect
    screen=cv2.cvtColor(np.array(pyautogui.screenshot()),cv2.COLOR_RGB2BGR)
    return screen[y:y+h,x:x+w].copy()


def send_arrow(key_name, duration, backend="pynput"):
    """Emite uma tecla Arrow via pynput para a aplicação atualmente focada."""
    if backend == "pyautogui":
        pyautogui.keyDown(key_name); time.sleep(duration); pyautogui.keyUp(key_name)
        return
    key_map={"up":keyboard.Key.up,"down":keyboard.Key.down,"left":keyboard.Key.left,"right":keyboard.Key.right}
    controller=keyboard.Controller()
    key=key_map[key_name]
    controller.press(key)
    time.sleep(duration)
    controller.release(key)


def locate_bright_target(frame, expected, radius=120):
    """Detecta o brilho do alvo; retorna posição e dados para auditar o detector."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    x,y = expected
    x0,y0=max(0,x-radius),max(0,y-radius); x1,y1=min(gray.shape[1],x+radius),min(gray.shape[0],y+radius)
    patch=gray[y0:y1,x0:x1]
    if patch.size == 0: return expected,{"method":"empty_search","confidence":0.0,"area":0,"threshold":None}
    threshold=max(150,int(np.percentile(patch,95)))
    mask=cv2.inRange(patch,threshold,255)
    n, labels, stats, cents=cv2.connectedComponentsWithStats(mask,8)
    candidates=[]
    for i in range(1,n):
        area=stats[i,cv2.CC_STAT_AREA]
        if 12 <= area <= 40000:
            cx,cy=cents[i]; gx,gy=int(cx+x0),int(cy+y0)
            dist=math.hypot(gx-x,gy-y)
            if dist<=radius:
                # Proximidade domina, mas em empate prefere o componente maior,
                # que corresponde melhor à esfera do que a partículas do brilho.
                score=dist-0.015*math.sqrt(area)
                candidates.append((score,dist,(gx,gy),area))
    if not candidates:
        return expected,{"method":"no_bright_component","confidence":0.0,"area":0,"threshold":threshold}
    _,dist,point,area=min(candidates)
    confidence=max(0.0,min(1.0,1.0-dist/max(1,radius)))*min(1.0,math.sqrt(area)/28)
    return point,{"method":"bright_component","confidence":round(confidence,3),"area":int(area),
                  "distance_from_previous_px":round(dist,2),"threshold":threshold}


def local_bright_target(frame, expected, radius=55):
    """Compatibilidade: retorna somente a coordenada do detector auditável."""
    return locate_bright_target(frame,expected,radius)[0]


def make_path(frame, start, goal, grid_scale=SCALE):
    """BFS em mapa visual reduzido; chão é a região mais escura do tabuleiro."""
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    # O brilho do chão ocupa a faixa escura; os contornos claros são paredes.
    # Otsu separa a faixa escura do piso da faixa clara das paredes sem
    # presumir qual proporção da tela cada uma ocupa.
    cutoff,_=cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    walk=(gray < cutoff).astype(np.uint8)
    # Fechar pequenas lacunas e engrossar as paredes para reduzir colisões.
    walk=cv2.morphologyEx(walk,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    walls=1-walk
    walls=cv2.dilate(walls,np.ones((5,5),np.uint8),iterations=1)
    walk=1-walls
    small=cv2.resize(walk,(max(1,walk.shape[1]//grid_scale),max(1,walk.shape[0]//grid_scale)),interpolation=cv2.INTER_NEAREST)
    h,w=small.shape
    def cell(p): return (min(w-1,max(0,p[0]//grid_scale)),min(h-1,max(0,p[1]//grid_scale)))
    s,g=cell(start),cell(goal)
    # Permitir localização no chão mais próximo se o efeito luminoso cobrir a célula.
    def nearest(c):
        if small[c[1],c[0]]: return c
        max_radius=max(12,min(max(w,h),int(180/grid_scale)))
        for r in range(1,max_radius+1):
            for yy in range(max(0,c[1]-r),min(h,c[1]+r+1)):
                for xx in range(max(0,c[0]-r),min(w,c[0]+r+1)):
                    if small[yy,xx] and abs(xx-c[0])+abs(yy-c[1])<=r+1: return (xx,yy)
        return c
    s,g=nearest(s),nearest(g)
    q=deque([s]); prev={s:None}
    while q:
        p=q.popleft()
        if p==g: break
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            z=(p[0]+dx,p[1]+dy)
            if 0<=z[0]<w and 0<=z[1]<h and small[z[1],z[0]] and z not in prev:
                prev[z]=p; q.append(z)
    if g not in prev:
        layer=np.zeros_like(frame)
        layer[walk>0]=(0,220,0); layer[walk==0]=(0,0,220)
        debug=cv2.addWeighted(frame,0.62,layer,0.38,0)
        cv2.circle(debug,(start[0],start[1]),12,(0,255,255),3)
        cv2.circle(debug,(goal[0],goal[1]),12,(255,255,255),3)
        cv2.putText(debug,f"Otsu={cutoff:.0f} walkable={100*np.mean(walk):.1f}% | yellow=start white=goal",(12,28),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),2,cv2.LINE_AA)
        cv2.imwrite(str(ROOT / "maze_mapa_diagnostico.png"),debug)
        print(f"Diagnóstico: Otsu={cutoff:.0f}, piso={100*np.mean(walk):.1f}% do tabuleiro; mapa salvo em maze_mapa_diagnostico.png")
        return []
    path=[]; p=g
    while p is not None: path.append((p[0]*grid_scale+grid_scale//2,p[1]*grid_scale+grid_scale//2)); p=prev[p]
    return path[::-1]


def log_step(entry, session_log=None):
    with LOG.open("a",encoding="utf-8") as f: f.write(json.dumps(entry,ensure_ascii=False)+"\n")
    if session_log is not None:
        with session_log.open("a",encoding="utf-8") as f:
            f.write(json.dumps(entry,ensure_ascii=False)+"\n")


def save_frame(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), frame)


def write_session(session_dir, metadata):
    session_dir.mkdir(parents=True, exist_ok=True)
    with (session_dir / "session.json").open("w",encoding="utf-8") as f:
        json.dump(metadata,f,ensure_ascii=False,indent=2)


def main():
    print("Agente Maze: Path of Light. Posicione o jogo visível e sem menus.")
    config=load_config()
    rect=select_rect("Selecione o tabuleiro inteiro, incluindo bola e portal; confirme com ENTER")
    while True:
        frame=capture(rect)
        points=pick_points(frame)
        if points is not None: break
        rect=select_rect("Refaça o recorte para incluir a bola e o portal")
    ball,portal=points
    current_ball=ball
    session_id=datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+uuid.uuid4().hex[:6]
    session_dir=DATA_ROOT/session_id
    frames_dir=session_dir/"frames"
    session_log=session_dir/"events.jsonl"
    metadata={"session_id":session_id,"started_at":datetime.now().astimezone().isoformat(timespec="seconds"),
              "status":"calibrated_waiting_for_start",
              "board_region_screen_px":{"x":rect[0],"y":rect[1],"width":rect[2],"height":rect[3]},
              "board_size_px":{"width":int(frame.shape[1]),"height":int(frame.shape[0])},
              "ball_calibration_px":ball,"portal_calibration_px":portal,
              "python":platform.python_version(),"platform":platform.platform(),"opencv":cv2.__version__,"numpy":np.__version__,
              "path_planner":"BFS on Otsu thresholded image","grid_scale_px":config["grid_scale_px"],
              "key_hold_seconds":config["key_hold_seconds"],"observation_delay_seconds":config["observation_delay_seconds"],
              "configuration":config.copy(),"input_backend":config["input_backend"],
              "notes":"Snapshots document screen observations; detector outcome labels are not verified ground truth."}
    write_session(session_dir,metadata)
    save_frame(frame,frames_dir/"calibration.png")
    log_step({"event_type":"session_started","session_id":session_id,"time":metadata["started_at"],
              "calibration_image":str((frames_dir/"calibration.png").relative_to(ROOT))},session_log)
    stop=threading.Event()
    start=threading.Event()
    def on_press(key):
        if key == keyboard.Key.f8:
            stop.set(); print("F8: encerrando com segurança..."); return False
        if key == keyboard.Key.f9:
            start.set()
    listener=keyboard.Listener(on_press=on_press); listener.start()
    print("Clique no jogo e pressione F9 para começar. O comando F9 inicia o controle após você focar o navegador.")
    print("F8 encerra a qualquer momento.")
    while not start.wait(0.1) and not stop.is_set():
        pass
    if stop.is_set():
        metadata["status"]="stopped_before_start"; metadata["ended_at"]=datetime.now().astimezone().isoformat(timespec="seconds"); write_session(session_dir,metadata)
        listener.stop(); print("Memória salva (nenhum movimento enviado)."); return
    metadata["status"]="running"; metadata["started_control_at"]=datetime.now().astimezone().isoformat(timespec="seconds"); write_session(session_dir,metadata)
    print("Rodando. F8 encerra.")
    move_num=0
    no_path_count=0
    try:
        while not stop.is_set():
            frame=capture(rect)
            current_ball,ball_detection_before=locate_bright_target(frame,current_ball,config["target_radius_px"])
            current_portal=local_bright_target(frame,portal,75)
            path=make_path(frame,current_ball,current_portal,config["grid_scale_px"])
            if len(path)<2:
                no_path_count+=1
                diagnostic=ROOT/"maze_mapa_diagnostico.png"
                log_step({"event_type":"planning_failure","session_id":session_id,"time":datetime.now().astimezone().isoformat(timespec="seconds"),
                          "move":move_num+1,"ball_before":current_ball,"portal":current_portal,"failure":"no_path_found",
                          "observation_image":str(diagnostic.relative_to(ROOT)) if diagnostic.exists() else None},session_log)
                print("Não consegui montar uma rota. Não vou pedir calibração repetidamente.")
                print(f"Tentativa sem rota {no_path_count}/3. Vou esperar a animação e observar de novo.")
                print("Confira maze_mapa_diagnostico.png: verde=piso detectado, vermelho=parede, amarelo=bola, branco=portal.")
                if no_path_count>=3: break
                time.sleep(0.45)
                continue
            no_path_count=0
            # Avança apenas um segmento curto por ciclo e confirma o deslocamento visualmente.
            target=path[min(len(path)-1, max(1, round(34/config["grid_scale_px"]))) ]
            dx,dy=target[0]-current_ball[0],target[1]-current_ball[1]
            key="right" if abs(dx)>=abs(dy) and dx>0 else "left" if abs(dx)>=abs(dy) else "down" if dy>0 else "up"
            before=current_ball
            before_frame=frame.copy()
            action_started=datetime.now().astimezone()
            send_arrow(key,config["key_hold_seconds"],config["input_backend"])
            time.sleep(config["observation_delay_seconds"])
            after_frame=capture(rect); observed,ball_detection_after=locate_bright_target(after_frame,before,config["target_radius_px"])
            dist_before=math.dist(before,current_portal); dist_after=math.dist(observed,current_portal)
            moved=math.dist(before,observed)>config["movement_threshold_px"]
            success=dist_after < 18
            move_num+=1
            before_name=f"move_{move_num:05d}_before.png"; after_name=f"move_{move_num:05d}_after.png"
            save_frame(before_frame,frames_dir/before_name); save_frame(after_frame,frames_dir/after_name)
            record={"event_type":"movement","session_id":session_id,"time":action_started.isoformat(timespec="seconds"),"move":move_num,"key":key,
                    "ball_before":before,"ball_after":observed,"portal":current_portal,
                    "ball_detection_before":ball_detection_before,"ball_detection_after":ball_detection_after,
                    "moved":moved,"closer_to_goal":dist_after<dist_before,"success":success,
                    "distance_to_portal_before_px":round(dist_before,2),"distance_to_portal_after_px":round(dist_after,2),
                    "path_cells":len(path),"key_hold_seconds":config["key_hold_seconds"],"observation_delay_seconds":config["observation_delay_seconds"],
                    "image_before":str((frames_dir/before_name).relative_to(ROOT)),"image_after":str((frames_dir/after_name).relative_to(ROOT)),
                    "outcome":"success" if success else "progress" if dist_after<dist_before else "blocked_or_wrong"}
            log_step(record,session_log)
            current_ball=observed
            print(f"{move_num}: {key} | {'andou' if moved else 'sem deslocamento'} | {record['outcome']} | "
                  f"detector={ball_detection_after['method']} area={ball_detection_after['area']} "
                  f"confianca={ball_detection_after['confidence']} pos={observed}")
            if not moved:
                fail_count = fail_count + 1 if 'fail_count' in locals() else 1
                if fail_count >= 2:
                    cv2.imwrite(str(ROOT / "maze_sem_movimento.png"),after_frame)
                    log_step({"event_type":"movement_failure","session_id":session_id,"time":datetime.now().astimezone().isoformat(timespec="seconds"),
                              "move":move_num,"reason":"ball_position_unchanged_twice","diagnostic_image":"maze_sem_movimento.png"},session_log)
                    print("A bola não mudou de posição após dois comandos. Parei para evitar teclas repetidas.")
                    print("A imagem observada foi salva em maze_sem_movimento.png. Verifique foco do navegador, seleção e se a seta funciona manualmente.")
                    break
            else:
                fail_count=0
            if success:
                print("Objetivo alcançado. Aguardando a próxima fase...")
                log_step({"event_type":"level_completed","session_id":session_id,"time":datetime.now().astimezone().isoformat(timespec="seconds"),"move":move_num},session_log)
                time.sleep(1.2)
                while True:
                    frame=capture(rect); points=pick_points(frame)
                    if points is not None: break
                    rect=select_rect("Selecione novamente um recorte que inclua bola e portal")
                ball,portal=points; current_ball=ball
            # Uma pausa curta também permite a animação terminar antes da próxima leitura.
            time.sleep(0.12)
    except pyautogui.FailSafeException:
        print("Fail-safe do mouse acionado; agente encerrado.")
    finally:
        stop.set(); listener.stop()
        metadata["ended_at"]=datetime.now().astimezone().isoformat(timespec="seconds")
        metadata["status"]="stopped" if move_num else "finished_without_moves"
        metadata["movement_count"]=move_num
        write_session(session_dir,metadata)
        log_step({"event_type":"session_ended","session_id":session_id,"time":metadata["ended_at"],"status":metadata["status"],"movement_count":move_num},session_log)
        print(f"Registros desta sessão: {session_dir}")
        print(f"Histórico global: {LOG.name}; execute dataset_export.py e export_results.py para preparar os arquivos da documentação.")


if __name__ == "__main__":
    main()


