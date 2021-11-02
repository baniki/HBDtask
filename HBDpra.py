#!/usr/bin/env python
# -*- coding: utf-8 -*-

####################
# -- 実験の概要 -- #
####################
# ボックスをクリックすると実験が始まる。
# 毎試行、R波（0〜+500ms）に合わせて、音（5回、100ms,100Hz）がなる
# 参加者は、自分の心拍と同期しているかをキー押しで回答する
# 何もせずに5秒経過すると「Hurry up!」というプロンプトが表示される。
# 回答後、正解不正解のフィードバックが1秒間表示される。
# これを各条件15回、90試行繰り返す。
# 30回ごとに休憩がある
# 試行の順序はランダマイズされる。
# 各試行の終わりにデータが記録される。
# 最終的にCSVとlogが保存される。

####################
# -- ライブラリ -- #
####################

# PsychoPy 2020.2.3で検証しています

from __future__ import division
from psychopy import core, data, event, gui, logging, visual, sound
from psychopy.hardware import keyboard
import numpy as np
import numpy.matlib
import pandas as pd
import sys
import struct
import time
import csv, os
import random
import psychtoolbox as ptb

import biopacndt_py3

############################
# -- ダイアログボックス -- #
############################

# ダイアログボックスを呈示し、参加者の情報を入力
subj_info = {"subj_id": "", "add_here_what_you_want": ""}
dialogue_box = gui.DlgFromDict(subj_info, order = ["subj_id", "add_here_what_you_want"])

# OKならID（subj_id）を記録して実験を進める。キャンセルなら実験を中止
if dialogue_box.OK:
    subj_id = subj_info["subj_id"]
else:
    core.quit()

####################
# -- 実験の設定 -- #
####################

# 現在日時を記録
exp_date = data.getDateStr("%Y%m%d")

# データファイルを保存するフォルダを作る
# フォルダがなければ作る
try:
    os.makedirs("data/pra")
    os.makedirs("data/log")
# フォルダが既にある場合は何もしない
except OSError:
    pass

# データファイルの名前を作る（ID_日付）
file_name = exp_date + subj_id + "_pra" 
file_name_csv = os.path.join("data/pra/" + file_name + ".csv")
file_name_log = os.path.join("data/log/" + file_name + ".log")

# 実験の条件
HBDcnd = [0.23,0.53]
nRestTrial = 20
reptition = 3

HBDList = HBDcnd*reptition
random.shuffle(HBDList)
maxTrial = len(HBDList)
trial_index = 0
print(HBDList)

#R波の検出条件
threshold = 0.8
interval = 0.6

########################################
# -- 画面、マウス、キーボードの設定 -- #
########################################

# 画面の座標系　units = "norm"
# 画面中心が(0, 0)、X軸が-1〜+1、Y軸が-1〜+1
win = visual.Window(size = (800, 600), units = "norm")
mouse = event.Mouse()
kb = keyboard.Keyboard()

####################
# -- 刺激を定義 -- #
####################

# テキスト刺激の色と日本語フォント
color_default, color_highlight = "white", "yellow"
font_ja = "ヒラギノ角ゴシック W5"

# キー設定
key_left, key_right = "f", "j"
key_space = "space"

# キーのテキストをX軸、Y軸方向にどれくらいずらすか
# 刺激（yes/no）
key_text_nudge_x = 0.5
key_text_nudge_y = 0
Q_text_nudge_x = 0
Q_text_nudge_y = 0.5
key_left_text = visual.TextStim(win, text = "synchronous(f)", pos = (-key_text_nudge_x, key_text_nudge_y))
key_right_text = visual.TextStim(win, text = "asynchronous(j)", pos = (key_text_nudge_x, key_text_nudge_y))
Q_text = visual.TextStim(win, text = "Is this sound synchronized with your heartbeat?",pos = (Q_text_nudge_x, Q_text_nudge_y))

# 教示を定義
inst_text = visual.TextStim(win, alignText = "left", anchorHoriz = "center")
inst_text.setText("""

You will hear 10 sequential tone sounds.
If you feel tone sounds were synchronous with your own heartbeat, click "f" key.
Otherwise, click "j" key.

Click space key and work on the task.
""")

# ボックスの線の太さ
box_line_width = 10

# 開始ボタンのボックスとテキスト
start_pos_y = -0.5 # Y軸座標
start_box = visual.Rect(win, width = 0.2, height = 0.2, pos = (0, start_pos_y), lineWidth = box_line_width)
start_text = visual.TextStim(win, text = "Click space key to Start", pos = (0, start_pos_y))

# 試行間で呈示するテキスト（テキストの中身は毎試行変えるので、後で定義する）
iti_text = visual.TextStim(win)
# ITIの長さ
iti_length = 1

# yes/noを選んだかを何秒呈示するか
confirmation_length = 1
# 選んだ方の回答を囲うボックスを定義
res_box_width, res_box_height = 0.6, 0.2 # ボックスのサイズ
res_box_left = visual.Rect(win,
    width = res_box_width, height = res_box_height, pos = (-key_text_nudge_x, 0),
    lineColor = color_highlight, lineWidth = box_line_width
)
res_box_right = visual.Rect(win,
    width = res_box_width, height = res_box_height, pos = (key_text_nudge_x, 0),
    lineColor = color_highlight, lineWidth = box_line_width
)

# プロンプトのテキスト
hurry_text = visual.TextStim(win, text = "Hurry up!", pos = (0, 0.8), color = color_highlight)
# time_limit秒経過したらプロンプトを出す
time_limit = 5

####################
# -- ログの設定 -- #
####################

# ログファイルの設定
file_log = logging.LogFile(file_name_log, level = logging.EXP)

##############
# -- 教示 -- #
##############

# 教示（無限ループ）
while True:

    # Startにカーソルが載ってたら黄色に
    #if start_box.contains(mouse):
        #start_box.setLineColor(color_highlight)
        #start_text.setColor(color_highlight)
    # 載ってなければ白に
    #else:
        #start_box.setLineColor(color_default)
        #start_text.setColor(color_default)

    # 教示とボックスを描画
    inst_text.draw()
    #start_box.draw()
    #start_text.setColor(color_highlight)
    #start_text.draw()
    win.flip()

            
    key = kb.getKeys(keyList = [key_space], waitRelease = False)

    # 開始ボタンがクリックされたら無限ループを抜ける
    if len(key) > 0:
        break
    #if mouse.isPressedIn(start_box):
        #break

# CSVファイルの先頭行に変数名を書き込む
with open(file_name_csv, "a", encoding = "cp932") as f:
    writer = csv.writer(f, lineterminator = "\n")
    writer.writerow([
        "subj_id", "trial", "delay", 
        "rt", "key", "ans","con"
    ])

#feedbackの関数を定義
Data = []
Time = time.perf_counter()
Maxnum = 10

def ProcessNDTdata(index, frame, channelsInSlice):
    global Time, Data, count,T,Maxnum
    if count < Maxnum:
        Data.append(frame[0])

        #閾値を超えていたらbeep音を鳴らす
        if len(Data) >= 1000:
            if threshold < Data[-1]:
                if (Data[-2]-Data[-3])*(Data[-1]-Data[-2]) <= 0:
                        now = ptb.GetSecs()
                        duration = time.perf_counter()-Time
                        Time = time.perf_counter()
                        print('beep',Data[-1],Data[-2],Data[-3],count+1,duration,T)
                        Data = []
                        mySound = sound.Sound(value="440", secs=0.05)
                        core.wait(T)
                        mySound.play()
                        now2=ptb.GetSecs()
                        print(now,now2)
                        count += 1

#AcqKnowledgeとの接続
acqServer = biopacndt_py3.AcqNdtQuickConnect() # Connect to AcqKnowledge
if not acqServer: # If no AcqKnowledge server is available, we quit at this point:
    status.message('No AcqKnowledge servers found!')
    time.sleep(2); 	sys.exit()
# Change data connection method to single. Learn more in the NDT help file:
if acqServer.getDataConnectionMethod() != "single": 
    acqServer.changeDataConnectionMethod("single")
    
enabledChannels = acqServer.DeliverAllEnabledChannels()	#get a list of all enabled channels
singleConnectPort = acqServer.getSingleConnectionModePort() #get the port for the connection
dataServer = biopacndt_py3.AcqNdtDataServer(singleConnectPort, enabledChannels ) #set up the data server
dataServer.RegisterCallback("ProcessNDTdata",ProcessNDTdata) # Call a function when data come in

##############
# -- 課題 -- #
##############

# カーソルを消す
mouse.setVisible(False)

# 課題開始
for T in HBDList:

    trial_index += 1
    # 試行間のテキストを定義して描画
    iti_text.setText(str(trial_index) + "/" + str(maxTrial))
    iti_text.draw()
    win.flip()
    core.wait(1)

    # 刺激テキストをセット
    delay = str(T)

    #フィードバックのプログラムを動かす
    count = 0
    start = time.perf_counter()
    
    if acqServer.getAcquisitionInProgress():
        pass
    else:
        dataServer.Start() #Start the dataserver
        acqServer.toggleAcquisition()
    
    time.sleep(12)
    # 刺激を描画
    key_left_text.draw()
    key_right_text.draw()
    Q_text.draw()
    win.flip()
        
    # 回答を待ち始めた時間をresp_onsetとして記録
    resp_onset = core.Clock()

    # キー押しをリセット
    kb.getKeys([key_left, key_right], waitRelease = False)
    kb.clock.reset()

    # 回答を待つ（無限ループ）
    while True:
        # FかJのキー押しを待つ
        key_pressed = kb.getKeys(keyList = [key_left, key_right], waitRelease = False)

        # もしFかJが押されたら
        if len(key_pressed) > 0:
            # 反応時間を記録
            rt = key_pressed[0].rt
                                    
            # どっちのキーを押したかをkeyとして記録
            # 選んだ方を黄色にする、四角で囲う
            if key_pressed[0].name == key_left:
                key = key_left
                ans = 1
                key_left_text.setColor(color_highlight)
                res_box_left.draw()
            else:
                key = key_right
                ans = 0
                key_right_text.setColor(color_highlight)
                res_box_right.draw()

            # 結果を記録
            # #if choice == answer:
            # #result = "correct"
            # #else:
            # #result = "wrong"
                                    
            # その他の刺激も描画して、1秒間呈示
            key_left_text.draw()
            key_right_text.draw()
            Q_text.draw()
            win.flip()
            core.wait(confirmation_length)
                                    
            # 刺激の色をリセットし、無限ループから抜ける
            key_left_text.setColor(color_default)
            key_right_text.setColor(color_default)
            break
    
    #キー押しをリセット
    kb.getKeys(['1','2','3','4','5','6','7'], waitRelease = False)
    kb.clock.reset()
    
    #自信度を入力
    while True:
        con_text = visual.TextStim(win, text = """
        Please answer your confidence on 7 scale 
        from very low(1) to very high(7)
        """)
        con_text.draw()
        win.flip()
        con_key = kb.getKeys(keyList = ['1','2','3','4','5','6','7'], waitRelease = False)
        if len(con_key) > 0:
            con = con_key[0].name
            break

    # R波フィードバック
    #feedback_text = visual.TextStim(win, text = "R+"+str(int(T*1000))+"ms")
    #feedback_text.draw()
    #win.flip()
    #core.wait(1)
    wait_text = visual.TextStim(win, text = "wait...")
    wait_text.draw()
    win.flip()
    core.wait(4)
                            
    # CSVファイルにデータを記録
    with open(file_name_csv, "a", encoding = "cp932") as f:
        writer = csv.writer(f, lineterminator = "\n")
        writer.writerow([
            subj_id, trial_index, delay, rt, key, ans, con
            ])
    # ログファイルを保存
    logging.flush()

    #休憩のタイミングの設定
    if trial_index % nRestTrial == 0 and trial_index != maxTrial:
        time.sleep(1)
        while True:
            rest_text = visual.TextStim(win, text = "enter space key to go to next block")
            rest_text.draw()
            win.flip()
            key = kb.getKeys(keyList = [key_space], waitRelease = False)
            if len(key) > 0:
                break

##################
# -- 実験終了 -- #
##################

#Acknowledgeの終了
if acqServer.getAcquisitionInProgress():
    acqServer.toggleAcquisition()

# 終わりの画面を定義
finish_text = visual.TextStim(win)
finish_text.setText("""
Finish! Thanks!
""")

# 3秒呈示してから実験終了
finish_text.draw()
win.flip()
core.wait(3)
win.close()
core.quit()