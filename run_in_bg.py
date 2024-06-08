from app import app
from betting_utils import live_betting, register_open_bet, open_bet_garbage_collector
import time

total_minutes = 0

with app.app_context():
    while True:
        print(total_minutes)
        if total_minutes == 120:
            open_bet_garbage_collector()
            register_open_bet()
            total_minutes = 0
        live_betting()
        total_minutes += 1
        time.sleep(60)

# latest process id: kmcron
# tmux attach-session -t kmcron
# tmux kill-session -t kmcron
# tmux ls
# tmux new -s kmcron
