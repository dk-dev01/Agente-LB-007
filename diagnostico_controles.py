"""Diagnostica setas manuais, foco do navegador e leitura visual da bola."""
from datetime import datetime
from pathlib import Path
import math
import json
import threading
import time
import uuid

try:
    import cv2
    from pynput import keyboard
    import maze_agent as maze
except ModuleNotFoundError as exc:
    print(f"Dependência ausente: {exc.name}. Rode: python -m pip install -r requirements.txt")
    raise SystemExit(1) from exc

ROOT=Path(__file__).resolve().parent


def pick_ball(frame):
    h,w=frame.shape[:2]
    scale=min(1.0,1000/w,650/h)
    view=cv2.resize(frame,(round(w*scale),round(h*scale)),interpolation=cv2.INTER_AREA) if scale<1 else frame.copy()
    point=[]
    def click(event,x,y,flags,param):
        if event==cv2.EVENT_LBUTTONDOWN and not point:
            point.append((int(x/scale),int(y/scale)))
            cv2.circle(view,(x,y),10,(0,255,255),2); cv2.imshow("Calibre somente a bola",view)
    cv2.namedWindow("Calibre somente a bola",cv2.WINDOW_NORMAL)
    cv2.putText(view,"Clique na bola | R refaz recorte | ESC cancela",(12,28),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),2,cv2.LINE_AA)
    cv2.imshow("Calibre somente a bola",view); cv2.setMouseCallback("Calibre somente a bola",click)
    print("A bola precisa estar visível neste recorte. Clique no centro; R refaz o recorte; ESC cancela.")
    while not point:
        key=cv2.waitKey(30)&0xff
        if key in (ord('r'),ord('R')):
            cv2.destroyWindow("Calibre somente a bola"); return None
        if key==27:
            cv2.destroyWindow("Calibre somente a bola"); raise RuntimeError("Calibração cancelada")
    cv2.destroyWindow("Calibre somente a bola")
    return point[0]


def main():
    print("Diagnóstico: selecione o tabuleiro inteiro e inclua a bola na região.")
    while True:
        rect=maze.select_rect("Selecione um recorte que inclua a bola; confirme vendo somente o recorte")
        frame=maze.capture(rect)
        ball=pick_ball(frame)
        if ball is not None: break
    run_id=datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+uuid.uuid4().hex[:5]
    folder=ROOT/"diagnosticos"/run_id
    folder.mkdir(parents=True,exist_ok=True)
    before_path=folder/"inicio.png"
    cv2.imwrite(str(before_path),frame)
    events_path=folder/"eventos.jsonl"
    stop=threading.Event(); active=threading.Event(); held=set(); lock=threading.Lock(); counter=[0]; ball_ref=[ball]

    def append(row):
        with events_path.open("a",encoding="utf-8") as f: f.write(json.dumps(row,ensure_ascii=False)+"\n")

    append({"event":"diagnostic_started","time":datetime.now().astimezone().isoformat(timespec="seconds"),
            "board_region_screen_px":{"x":rect[0],"y":rect[1],"width":rect[2],"height":rect[3]},
            "ball_calibration_px":ball,"initial_image":str(before_path.relative_to(ROOT))})
    print("Clique no jogo e pressione F9. Depois pressione as setas MANUALMENTE, uma por vez.")
    print("F8 encerra. Setas manuais são registradas; pressione T para testar uma seta sintética à direita.")

    def observe(key_name, image_before, ball_before, detection_before, synthetic=False):
        if synthetic:
            maze.send_arrow("right",0.45,"pynput")
        time.sleep(0.7)
        image_after=maze.capture(rect)
        ball_after,detection_after=maze.locate_bright_target(image_after,ball_before,300)
        moved=math.dist(ball_before,ball_after)>3
        with lock:
            counter[0]+=1; idx=counter[0]
            if moved: ball_ref[0]=ball_after
        p_before=folder/f"{idx:03d}_{key_name}_antes.png"; p_after=folder/f"{idx:03d}_{key_name}_depois.png"
        cv2.imwrite(str(p_before),image_before); cv2.imwrite(str(p_after),image_after)
        append({"event":"synthetic_arrow_test" if synthetic else "manual_arrow","time":datetime.now().astimezone().isoformat(timespec="seconds"),
                "key":key_name,"ball_before_px":ball_before,"ball_after_px":ball_after,"movement_detected":moved,
                "detection_before":detection_before,"detection_after":detection_after,
                "image_before":str(p_before.relative_to(ROOT)),"image_after":str(p_after.relative_to(ROOT)),
                "interpretation":"bola mudou na captura" if moved else "sem mudança visual detectada; confira imagens"})
        print(f"{key_name}: {'movimento detectado' if moved else 'sem mudança detectada'}; "
              f"detector={detection_after['method']}, area={detection_after['area']} px, "
              f"confiança={detection_after['confidence']} — imagens em {folder}")

    def on_press(key):
        if key==keyboard.Key.f8:
            stop.set(); return False
        if key==keyboard.Key.f9:
            active.set(); print("Teste ativo: pressione uma seta manualmente."); return
        if key==keyboard.KeyCode.from_char('t') and active.is_set():
            image=maze.capture(rect); point,details=maze.locate_bright_target(image,ball_ref[0],300)
            threading.Thread(target=observe,args=("synthetic_right",image,point,details,True),daemon=True).start()
            print("Enviando seta sintética para a direita."); return
        names={keyboard.Key.up:"up",keyboard.Key.down:"down",keyboard.Key.left:"left",keyboard.Key.right:"right"}
        name=names.get(key)
        if active.is_set() and name and name not in held:
            held.add(name)
            image=maze.capture(rect)
            point,details=maze.locate_bright_target(image,ball_ref[0],300)
            threading.Thread(target=observe,args=(name,image,point,details),daemon=True).start()

    def on_release(key):
        names={keyboard.Key.up:"up",keyboard.Key.down:"down",keyboard.Key.left:"left",keyboard.Key.right:"right"}
        if key in names: held.discard(names[key])

    listener=keyboard.Listener(on_press=on_press,on_release=on_release); listener.start()
    try:
        while not stop.wait(0.2): pass
    finally:
        listener.stop()
        append({"event":"diagnostic_ended","time":datetime.now().astimezone().isoformat(timespec="seconds"),"arrow_events":counter[0]})
        print(f"Diagnóstico salvo em {folder}")


if __name__=="__main__": main()
