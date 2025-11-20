
try:
    import pygame
except ImportError:
    import pygame_ce as pygame
import sys
import os
from enum import Enum
from copy import deepcopy
from collections import deque

# 初始化 Pygame
pygame.init()

# 常數定義
GRID_SIZE = 8
CELL_SIZE = 70
SIDEBAR_WIDTH = 300
WINDOW_WIDTH = GRID_SIZE * CELL_SIZE + SIDEBAR_WIDTH
WINDOW_HEIGHT = GRID_SIZE * CELL_SIZE
FPS = 60

# Catppuccin Mocha 調色盤
# https://catppuccin.com/palette/mocha
WHITE = (205, 214, 244)      # text
BLACK = (24, 24, 37)         # base
GRAY = (166, 173, 200)       # surface2
LIGHT_GRAY = (30, 30, 46)    # mantle
DARK_GRAY = (108, 112, 134)  # overlay1
RED = (243, 139, 168)        # red
GREEN = (166, 227, 161)      # green
BLUE = (137, 180, 250)       # blue
YELLOW = (249, 226, 175)     # yellow
PURPLE = (203, 166, 247)     # mauve
ORANGE = (250, 179, 135)     # peach
CYAN = (148, 226, 213)       # teal
DARK_BLUE = (108, 112, 134)  # overlay1
SHADOW = (49, 50, 68)        # crust
SIDEBAR_BG = (24, 25, 38)    # Catppuccin Mocha crust #181926
GRID_LINE = (181, 191, 226)  # Catppuccin Mocha subtext1 #b5bfe2，比格子本身更淡

MOCHA_CRUST = (24, 25, 38)   # #181926

class Direction(Enum):
    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class Game:
    def get_state(self):
        # 僅回傳遊戲狀態（用於存檔/回溯/撤銷）
        return {
            'player_pos': deepcopy(self.player_pos),
            'player_moves_left': self.player_moves_left,
            'enemies': deepcopy(self.enemies),
            'turn': self.turn,
            'max_turns': self.max_turns,
            'is_first_turn': self.is_first_turn,
            'player_turn': self.player_turn,
            'turn_start_player_pos': deepcopy(self.turn_start_player_pos),
            'turn_start_enemies': deepcopy(self.turn_start_enemies) if self.turn_start_enemies else None,
            'skill1_uses': self.skill1_uses,
            'skill2_uses': self.skill2_uses,
            'skill1_used_this_turn': self.skill1_used_this_turn,
            'skill2_used_this_turn': self.skill2_used_this_turn,
            'selected_skill': self.selected_skill,
            'stun_area': deepcopy(self.stun_area),
            'walls': deepcopy(self.walls),
            'one_way_doors': deepcopy(self.one_way_doors),
            'yellow_plate': deepcopy(self.yellow_plate),
            'yellow_plate_active': self.yellow_plate_active,
            'blue_plates': deepcopy(self.blue_plates),
            'green_plates': deepcopy(self.green_plates),
            'purple_plates': deepcopy(self.purple_plates),
            'doors': deepcopy(self.doors),
            'goal_pos': deepcopy(self.goal_pos),
            'game_won': self.game_won,
            'game_lost': self.game_lost,
            'action_log': deepcopy(self.action_log),
        }
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("銀與血 - 詭秘航路 - 軍械號 II - 四重奏 - 簡易小遊戲")
        self.clock = pygame.time.Clock()
        # 其餘初始化內容...
        # 載入中文字體、init_game 等原本內容請保留

        # 載入自訂中文字體（fonts/ChironGoRoundTC-Medium.ttf）
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "ChironGoRoundTC-Medium.ttf")
        if os.path.exists(font_path):
            self.font = pygame.font.Font(font_path, 28)
            self.small_font = pygame.font.Font(font_path, 20)
        else:
            self.font = pygame.font.Font(None, 28)
            self.small_font = pygame.font.Font(None, 20)
        # 初始化遊戲狀態
        self.init_game()
        
    def init_game(self):
        """初始化遊戲"""
        # 玩家位置 (2,2) - 注意座標轉換
        self.player_pos = [2, 2]
        self.player_moves_left = 6  # 每回合 6 步
        
        # 4 個敵人，都向右移動
        self.enemies = [
            {"pos": [1, 8], "dir": Direction.RIGHT, "stunned": 0},
            {"pos": [1, 7], "dir": Direction.RIGHT, "stunned": 0},
            {"pos": [1, 6], "dir": Direction.RIGHT, "stunned": 0},
            {"pos": [1, 5], "dir": Direction.RIGHT, "stunned": 0}
        ]
        
        # 回合系統
        self.turn = 1
        self.max_turns = 20
        self.is_first_turn = True
        self.player_turn = True  # 當前是否為玩家回合
        
        # 記錄回合開始時的狀態
        self.turn_start_player_pos = self.player_pos.copy()
        self.turn_start_enemies = None  # 第一回合敵人不移動，不記錄
        
        # 技能系統
        self.skill1_uses = 3  # 回溯技能
        self.skill2_uses = 3  # 靜止技能
        self.skill1_used_this_turn = False
        self.skill2_used_this_turn = False
        self.selected_skill = None  # 'skill1' or 'skill2'
        self.stun_area = None  # 靜止技能的顯示區域
        
        # 牆壁 (紅色線條)
        self.walls = set()
        self.init_walls()
        
        # 單向門
        self.one_way_doors = set()
        self.init_one_way_doors()
        
        # 壓版系統
        self.yellow_plate = [1, 3]
        self.yellow_plate_active = False
        self.blue_plates = [[5, 8], [5, 7], [5, 6]]
        self.green_plates = [[3, 7], [3, 6], [3, 5]]
        self.purple_plates = [[7, 8], [7, 7]]
        
        # 門系統 (位置是兩個格子之間)
        self.doors = {
            "yellow1": {"between": [[1, 6], [2, 6]], "open": False},
            "yellow2": {"between": [[1, 7], [2, 7]], "open": False},
            "yellow3": {"between": [[7, 8], [8, 8]], "open": False},
            "green": {"between": [[2, 2], [3, 2]], "open": False},
            "purple": {"between": [[4, 2], [5, 2]], "open": False},
            "blue": {"between": [[6, 2], [7, 2]], "open": False}
        }
        
        # 目標位置
        self.goal_pos = [7, 2]
        
        # 遊戲狀態
        self.game_won = False
        self.game_lost = False
        
        self.action_log = []  # 記錄當前回合的行動
        
        # 返回上一步功能
        self.history = []  # 儲存每一步的狀態
        self.redo_stack = []  # 撤銷後可重做的狀態
        
    def init_walls(self):
        """根據圖片初始化牆壁"""
        # 外圍牆壁 - 最外框正方形
        for x in range(1, 9):
            self.walls.add((x, 1, 'H'))  # 下邊界
            self.walls.add((x, 9, 'H'))  # 上邊界
        for y in range(1, 9):
            self.walls.add((1, y, 'V'))  # 左邊界
            self.walls.add((9, y, 'V'))  # 右邊界
        
        # 水平牆壁 - (x,y) 和 (x,y+1) 之間
        # (x,4) (x,5) 之間
        for x in [1, 2, 3, 4, 5, 6, 7, 8]:
            self.walls.add((x, 5, 'H'))
        
        # (x,5) (x,6) 之間
        for x in [1, 2, 3, 4, 5, 6]:
            self.walls.add((x, 6, 'H'))
        
        # (x,6) (x,7) 之間
        for x in [1, 2, 3, 4, 5, 6, 7]:
            self.walls.add((x, 7, 'H'))
        
        # (x,7) (x,8) 之間
        for x in [1, 2, 3, 4, 5, 6, 7, 8]:
            self.walls.add((x, 8, 'H'))
        
        # 垂直牆壁 - (x,y) 和 (x+1,y) 之間
        # (2,1) (3,1) 之間
        self.walls.add((3, 1, 'V'))
        
        # (2,4) (3,4) 之間
        self.walls.add((3, 4, 'V'))
        
        # (4,3) (5,3) 之間
        self.walls.add((5, 3, 'V'))
        
        # (4,4) (5,4) 之間
        self.walls.add((5, 4, 'V'))
        
        # (6,1) (7,1) 之間
        self.walls.add((7, 1, 'V'))
        
        # (6,3) (7,3) 之間
        self.walls.add((7, 3, 'V'))
        
        # (6,4) (7,4) 之間
        self.walls.add((7, 4, 'V'))
        
        # (4,5) (5,5) 之間
        self.walls.add((5, 5, 'V'))
        
        # (6,6) (7,6) 之間
        self.walls.add((7, 6, 'V'))
        
        # (7,7) (8,7) 之間
        self.walls.add((8, 7, 'V'))
        
    def init_one_way_doors(self):
        """初始化單向門"""
        # 單向門 1: (2,3) 和 (3,3) 之間，只能從 (3,3) 走到 (2,3)
        self.one_way_doors.add((2, 3, Direction.LEFT))
        
        # 單向門 2: (4,1) 和 (5,1) 之間，只能從 (5,1) 走到 (4,1)
        self.one_way_doors.add((4, 1, Direction.LEFT))
    
    def save_state(self):
        self.history.append(self.get_state())
        self.redo_stack.clear()  # 新動作後清空 redo
    
    def undo(self):
        """返回上一步（可跨回合）"""
        if not self.history:
            self.action_log.append("無法撤銷！")
            return False
        self.redo_stack.append(self.get_state())
        state = self.history.pop()
        self.set_state(state)
        return True

    def redo(self):
        """重做（返回撤銷前的狀態）"""
        if not self.redo_stack:
            self.action_log.append("無法重做！")
            return False
        self.history.append(self.get_state())
        redo_state = self.redo_stack.pop()
        self.set_state(redo_state)
        return True
    
    def find_path_bfs(self, start, goal):
        """使用 BFS 尋找從起點到終點的最短路徑"""
        if start == goal:
            return []
        
        queue = deque([(start, [])])
        visited = {tuple(start)}
        
        while queue:
            current, path = queue.popleft()
            
            # 檢查四個方向
            for dx, dy in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                next_pos = [current[0] + dx, current[1] + dy]
                next_tuple = tuple(next_pos)
                
                if next_tuple in visited:
                    continue
                
                if self.can_move(current, next_pos):
                    new_path = path + [(dx, dy)]
                    
                    if next_pos == goal:
                        return new_path
                    
                    queue.append((next_pos, new_path))
                    visited.add(next_tuple)
        
        return None  # 找不到路徑
    
    
    
    
    def coord_to_screen(self, x, y):
        """遊戲座標 (1-8) 轉換為螢幕座標，Y 軸翻轉"""
        screen_x = (x - 1) * CELL_SIZE
        screen_y = (8 - y) * CELL_SIZE
        return screen_x, screen_y
    
    def screen_to_coord(self, screen_x, screen_y):
        """螢幕座標轉換為遊戲座標 (1-8)"""
        x = screen_x // CELL_SIZE + 1
        y = 8 - (screen_y // CELL_SIZE)
        return x, y
    
    def draw_grid(self):
        """繪製格子（現代扁平風）"""
        # 背景
        # 使用 Catppuccin Mocha 最深色 crust
        self.screen.fill((24, 24, 37))  # Catppuccin Mocha crust #181825
        # 格子
        for x in range(1, 9):
            for y in range(1, 9):
                sx, sy = self.coord_to_screen(x, y)
                rect = pygame.Rect(sx, sy, CELL_SIZE, CELL_SIZE)
                # 陰影
                shadow_rect = pygame.Rect(sx + 3, sy + 3, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(self.screen, SHADOW, shadow_rect, border_radius=8)
                # 主格子
                pygame.draw.rect(self.screen, WHITE, rect, border_radius=8)
                # 邊框（更淡的灰色）
                pygame.draw.rect(self.screen, GRID_LINE, rect, 2, border_radius=8)
        # 牆壁
        for wall in self.walls:
            if len(wall) == 3:
                x, y, orientation = wall
                if orientation == 'H':
                    sx, sy = self.coord_to_screen(x, y)
                    pygame.draw.line(self.screen, MOCHA_CRUST, (sx + 8, sy + CELL_SIZE), (sx + CELL_SIZE - 8, sy + CELL_SIZE), 6)
                else:
                    sx, sy = self.coord_to_screen(x, y)
                    pygame.draw.line(self.screen, MOCHA_CRUST, (sx, sy + 8), (sx, sy + CELL_SIZE - 8), 6)
        # 壓板
        sx, sy = self.coord_to_screen(*self.yellow_plate)
        color = YELLOW if self.yellow_plate_active else (230, 220, 120)
        pygame.draw.rect(self.screen, color, (sx + 10, sy + 10, CELL_SIZE - 20, CELL_SIZE - 20), border_radius=10)
        # 藍色壓板
        for plate in self.blue_plates:
            sx, sy = self.coord_to_screen(*plate)
            pygame.draw.rect(self.screen, CYAN, (sx + 10, sy + 10, CELL_SIZE - 20, CELL_SIZE - 20), border_radius=10)
        # 綠色壓板
        for plate in self.green_plates:
            sx, sy = self.coord_to_screen(*plate)
            pygame.draw.rect(self.screen, GREEN, (sx + 10, sy + 10, CELL_SIZE - 20, CELL_SIZE - 20), border_radius=10)
        # 紫色壓板
        for plate in self.purple_plates:
            sx, sy = self.coord_to_screen(*plate)
            pygame.draw.rect(self.screen, PURPLE, (sx + 10, sy + 10, CELL_SIZE - 20, CELL_SIZE - 20), border_radius=10)
        # 門
        for door_name, door_info in self.doors.items():
            pos1, pos2 = door_info["between"]
            is_open = door_info["open"]
            if "yellow" in door_name:
                color = YELLOW
            elif "green" in door_name:
                color = GREEN
            elif "purple" in door_name:
                color = PURPLE
            elif "blue" in door_name:
                color = CYAN
            if pos1[1] == pos2[1]:
                y = pos1[1]
                x = max(pos1[0], pos2[0])
                sx, sy = self.coord_to_screen(x, y)
                if is_open:
                    for i in range(10, CELL_SIZE - 10, 14):
                        pygame.draw.line(self.screen, color, (sx, sy + i), (sx, sy + i + 8), 5)
                else:
                    pygame.draw.line(self.screen, color, (sx, sy + 10), (sx, sy + CELL_SIZE - 10), 10)
            else:
                x = pos1[0]
                y = max(pos1[1], pos2[1])
                sx, sy = self.coord_to_screen(x, y)
                if is_open:
                    for i in range(10, CELL_SIZE - 10, 14):
                        pygame.draw.line(self.screen, color, (sx + i, sy + CELL_SIZE), (sx + i + 8, sy + CELL_SIZE), 5)
                else:
                    pygame.draw.line(self.screen, color, (sx + 10, sy + CELL_SIZE), (sx + CELL_SIZE - 10, sy + CELL_SIZE), 10)
        # 單向門
        for door in self.one_way_doors:
            x, y, direction = door
            sx, sy = self.coord_to_screen(x, y)
            center_x = sx + CELL_SIZE // 2
            center_y = sy + CELL_SIZE // 2
            if direction == Direction.LEFT:
                pygame.draw.line(self.screen, DARK_BLUE, (center_x + 18, center_y), (center_x - 18, center_y), 4)
                pygame.draw.polygon(self.screen, DARK_BLUE, [
                    (center_x - 18, center_y),
                    (center_x - 8, center_y - 8),
                    (center_x - 8, center_y + 8)
                ])
        # 靜止技能範圍
        if self.stun_area:
            cx, cy = self.stun_area
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    tx, ty = cx + dx, cy + dy
                    if 1 <= tx <= 8 and 1 <= ty <= 8:
                        sx, sy = self.coord_to_screen(tx, ty)
                        s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                        s.fill((YELLOW[0], YELLOW[1], YELLOW[2], 70))
                        pygame.draw.rect(s, (255,255,255,40), (0,0,CELL_SIZE,CELL_SIZE), border_radius=10)
                        self.screen.blit(s, (sx, sy))
        # 目標位置
        sx, sy = self.coord_to_screen(*self.goal_pos)
        center = (sx + CELL_SIZE // 2, sy + CELL_SIZE // 2)
        pygame.draw.circle(self.screen, ORANGE, center, CELL_SIZE // 3)
        pygame.draw.circle(self.screen, WHITE, center, CELL_SIZE // 3 - 8)
        # 玩家
        sx, sy = self.coord_to_screen(*self.player_pos)
        center = (sx + CELL_SIZE // 2, sy + CELL_SIZE // 2)
        pygame.draw.circle(self.screen, DARK_BLUE, center, CELL_SIZE // 3)
        pygame.draw.circle(self.screen, WHITE, center, CELL_SIZE // 3 - 8)
        # 敵人
        for i, enemy in enumerate(self.enemies):
            # 預測位置
            if self.player_turn and not self.game_won and not self.game_lost:
                next_pos = self.predict_enemy_next_pos(enemy)
                nsx, nsy = self.coord_to_screen(*next_pos)
                next_center = (nsx + CELL_SIZE // 2, nsy + CELL_SIZE // 2)
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(s, (RED[0], RED[1], RED[2], 60), (CELL_SIZE // 2, CELL_SIZE // 2), CELL_SIZE // 3)
                self.screen.blit(s, (nsx, nsy))
                pygame.draw.circle(self.screen, RED, next_center, CELL_SIZE // 3, 2)
            sx, sy = self.coord_to_screen(*enemy["pos"])
            center = (sx + CELL_SIZE // 2, sy + CELL_SIZE // 2)
            pygame.draw.circle(self.screen, RED, center, CELL_SIZE // 3)
            pygame.draw.circle(self.screen, WHITE, center, CELL_SIZE // 3 - 8)
            # 標記敵人移動方向
            dir = enemy["dir"].value
            arrow_len = CELL_SIZE // 3 - 4
            # 算出箭頭終點
            dx, dy = dir
            # 方向轉螢幕座標（Y 軸反轉）
            screen_dx = dx * arrow_len
            screen_dy = -dy * arrow_len
            arrow_tip = (center[0] + screen_dx, center[1] + screen_dy)
            # 箭頭主體
            pygame.draw.line(self.screen, DARK_GRAY, center, arrow_tip, 4)
            # 箭頭三角形
            import math
            angle = math.atan2(screen_dy, screen_dx)
            left = (arrow_tip[0] - 10 * math.cos(angle - math.pi / 6), arrow_tip[1] - 10 * math.sin(angle - math.pi / 6))
            right = (arrow_tip[0] - 10 * math.cos(angle + math.pi / 6), arrow_tip[1] - 10 * math.sin(angle + math.pi / 6))
            pygame.draw.polygon(self.screen, DARK_GRAY, [arrow_tip, left, right])
            if enemy["stunned"] > 0:
                pygame.draw.circle(self.screen, PURPLE, center, CELL_SIZE // 3 + 6, 3)
    
    def draw_sidebar(self):
        """繪製側邊欄"""
        sidebar_rect = pygame.Rect(GRID_SIZE * CELL_SIZE, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, SIDEBAR_BG, sidebar_rect)
        
        x = GRID_SIZE * CELL_SIZE + 10
        y = 20
        
        # 回合資訊
        turn_text = self.font.render(f"回合：{self.turn}/{self.max_turns}", True, WHITE)
        self.screen.blit(turn_text, (x, y))
        y += 36
        # 剩餘步數
        moves_text = self.font.render(f"剩餘步數：{self.player_moves_left}/6", True, WHITE)
        self.screen.blit(moves_text, (x, y))
        y += 44
        
        # 判斷是否遊戲結束（勝利或失敗）
        game_over = self.game_won or self.game_lost

        # 技能 1 按鈕
        skill1_rect = pygame.Rect(x, y, 280, 40)
        if game_over:
            color = GRAY
        else:
            color = GREEN if self.skill1_uses > 0 and not self.skill1_used_this_turn else GRAY
            if self.selected_skill == 'skill1':
                color = ORANGE
        pygame.draw.rect(self.screen, color, skill1_rect)
        text = f"技能 1: 回溯 ({self.skill1_uses}/3)"
        if self.skill1_used_this_turn:
            text += " [已用]"
        # 技能按鈕用深色字
        text_surf = self.small_font.render(text, True, BLACK)
        text_rect = text_surf.get_rect(center=skill1_rect.center)
        self.screen.blit(text_surf, text_rect)
        self.skill1_button = skill1_rect
        y += 50

        # 技能 2 按鈕
        skill2_rect = pygame.Rect(x, y, 280, 40)
        if game_over:
            color = GRAY
        else:
            color = GREEN if self.skill2_uses > 0 and not self.skill2_used_this_turn else GRAY
            if self.selected_skill == 'skill2':
                color = ORANGE
        pygame.draw.rect(self.screen, color, skill2_rect)
        text = f"技能 2: 靜止 ({self.skill2_uses}/3)"
        if self.skill2_used_this_turn:
            text += " [已用]"
        # 技能按鈕用深色字
        text_surf = self.small_font.render(text, True, BLACK)
        text_rect = text_surf.get_rect(center=skill2_rect.center)
        self.screen.blit(text_surf, text_rect)
        self.skill2_button = skill2_rect
        y += 50

        # 撤銷按鈕
        undo_rect = pygame.Rect(x, y, 135, 50)
        undo_color = GRAY if game_over else (PURPLE if self.history else GRAY)
        pygame.draw.rect(self.screen, undo_color, undo_rect)
        text_surf = self.small_font.render(f"上一步 ({len(self.history)})", True, WHITE)
        text_rect = text_surf.get_rect(center=undo_rect.center)
        self.screen.blit(text_surf, text_rect)
        self.undo_button = undo_rect

        # 重做按鈕
        redo_rect = pygame.Rect(x + 145, y, 135, 50)
        redo_color = GRAY if game_over else (ORANGE if self.redo_stack else GRAY)
        pygame.draw.rect(self.screen, redo_color, redo_rect)
        text_surf = self.small_font.render(f"取消上一步 ({len(self.redo_stack)})", True, WHITE)
        text_rect = text_surf.get_rect(center=redo_rect.center)
        self.screen.blit(text_surf, text_rect)
        self.redo_button = redo_rect
        y += 55

        # 結束回合按鈕
        end_turn_rect = pygame.Rect(x, y, 135, 50)
        end_turn_color = GRAY if game_over else BLUE
        pygame.draw.rect(self.screen, end_turn_color, end_turn_rect)
        text_surf = self.small_font.render("結束回合", True, WHITE)
        text_rect = text_surf.get_rect(center=end_turn_rect.center)
        self.screen.blit(text_surf, text_rect)
        self.end_turn_button = end_turn_rect

        # 重新開始按鈕
        restart_rect = pygame.Rect(x + 145, y, 135, 50)
        pygame.draw.rect(self.screen, RED, restart_rect)
        text_surf = self.small_font.render("重新開始", True, WHITE)
        text_rect = text_surf.get_rect(center=restart_rect.center)
        self.screen.blit(text_surf, text_rect)
        self.restart_button = restart_rect
        y += 60
        
        # 行動記錄
        if self.action_log:
            log_title = self.font.render("本回合行動：", True, WHITE)
            self.screen.blit(log_title, (x, y))
            y += 30
            
            # 只顯示最近的 8 條記錄
            recent_logs = self.action_log[-8:]
            for log in recent_logs:
                log_surf = self.small_font.render(log, True, WHITE)
                self.screen.blit(log_surf, (x, y))
                y += 22
            y += 10
        
        # 說明文字
        help_texts = [
            "WASD/方向鍵：移動",
            "技能 1: 點選單位回溯",
            "技能 2: 點選格子靜止 (範圍 3x3)",
            "撤銷：返回上一步"
        ]
        
        for text in help_texts:
            text_surf = self.small_font.render(text, True, WHITE)
            self.screen.blit(text_surf, (x, y))
            y += 24
        
        # 遊戲結果
        if self.game_won:
            result_text = self.font.render("勝利！", True, GREEN)
            self.screen.blit(result_text, (x + 80, y + 20))
        elif self.game_lost:
            result_text = self.font.render("失敗！", True, RED)
            self.screen.blit(result_text, (x + 80, y + 20))
    
    def can_move(self, from_pos, to_pos):
        """檢查是否可以移動"""
        fx, fy = from_pos
        tx, ty = to_pos
        
        # 檢查邊界
        if not (1 <= tx <= 8 and 1 <= ty <= 8):
            return False
        
        # 檢查牆壁
        if fx != tx:  # 水平移動 (左右移動)
            # 從 fx 移動到 tx，需要檢查之間的垂直牆
            if tx > fx:  # 向右移動，檢查 tx 左邊的牆
                if (tx, fy, 'V') in self.walls:
                    return False
            else:  # 向左移動，檢查 fx 左邊的牆
                if (fx, fy, 'V') in self.walls:
                    return False
        
        if fy != ty:  # 垂直移動 (上下移動)
            # 從 fy 移動到 ty，需要檢查之間的水平牆
            if ty > fy:  # 向上移動，檢查 ty 下邊的牆
                if (fx, ty, 'H') in self.walls:
                    return False
            else:  # 向下移動，檢查 fy 下邊的牆
                if (fx, fy, 'H') in self.walls:
                    return False
        
        # 檢查門 (關閉的門視為牆壁)
        for door_info in self.doors.values():
            if not door_info["open"]:
                pos1, pos2 = door_info["between"]
                if [fx, fy] in [pos1, pos2] and [tx, ty] in [pos1, pos2]:
                    return False
        
        # 檢查單向門
        for door in self.one_way_doors:
            dx, dy, direction = door
            if direction == Direction.LEFT:
                # 只能從右到左
                if fy == dy and tx == dx and fx == dx + 1:
                    return True  # 正確方向
                elif fy == dy and fx == dx and tx == dx + 1:
                    return False  # 錯誤方向
        
        return True
    
    def move_player(self, dx, dy, log_action=True):
        """移動玩家"""
        if not self.player_turn or self.player_moves_left <= 0:
            return False
        new_pos = [self.player_pos[0] + dx, self.player_pos[1] + dy]
        if self.can_move(self.player_pos, new_pos):
            # 儲存移動前的狀態
            self.save_state()
            old_pos = self.player_pos.copy()
            self.player_pos = new_pos
            self.player_moves_left -= 1
            # 記錄行動
            if log_action:
                direction = ""
                if dx == 1: direction = "右"
                elif dx == -1: direction = "左"
                elif dy == 1: direction = "上"
                elif dy == -1: direction = "下"
                self.action_log.append(f"向{direction}移動：({old_pos[0]},{old_pos[1]}) → ({new_pos[0]},{new_pos[1]})")
            # 檢查黃色壓版
            if self.player_pos == self.yellow_plate:
                self.yellow_plate_active = not self.yellow_plate_active
                self.update_doors()
                if log_action:
                    status = "開啟" if self.yellow_plate_active else "關閉"
                    self.action_log.append(f"踩到黃色壓版！黃色門{status}")
            # 檢查是否到達目標
            if self.player_pos == self.goal_pos:
                self.game_won = True
                if log_action:
                    self.action_log.append("到達目標！勝利！")
            return True
        return False
    
    def update_doors(self):
        """更新門的狀態"""
        # 黃色門 (三個門都由黃色壓版控制)
        self.doors["yellow1"]["open"] = self.yellow_plate_active
        self.doors["yellow2"]["open"] = self.yellow_plate_active
        self.doors["yellow3"]["open"] = self.yellow_plate_active
        
        # 藍色門 - 檢查所有藍色壓版是否都被踩
        blue_count = sum(1 for enemy in self.enemies if enemy["pos"] in self.blue_plates)
        self.doors["blue"]["open"] = (blue_count == len(self.blue_plates))
        
        # 綠色門
        green_count = sum(1 for enemy in self.enemies if enemy["pos"] in self.green_plates)
        self.doors["green"]["open"] = (green_count == len(self.green_plates))
        
        # 紫色門
        purple_count = sum(1 for enemy in self.enemies if enemy["pos"] in self.purple_plates)
        self.doors["purple"]["open"] = (purple_count == len(self.purple_plates))
    
    def predict_enemy_next_pos(self, enemy):
        """預測敵人下一回合的位置"""
        # 如果敵人被靜止，下一回合不移動
        if enemy["stunned"] > 0:
            return enemy["pos"].copy()
        
        # 模擬敵人移動 4 步
        sim_pos = enemy["pos"].copy()
        sim_dir = enemy["dir"]
        
        for step in range(4):
            dx, dy = sim_dir.value
            new_pos = [sim_pos[0] + dx, sim_pos[1] + dy]
            
            if self.can_move(sim_pos, new_pos):
                sim_pos = new_pos
            else:
                # 反彈
                if sim_dir == Direction.RIGHT:
                    sim_dir = Direction.LEFT
                elif sim_dir == Direction.LEFT:
                    sim_dir = Direction.RIGHT
                elif sim_dir == Direction.UP:
                    sim_dir = Direction.DOWN
                else:
                    sim_dir = Direction.UP
                
                # 反彈後用新方向移動
                dx, dy = sim_dir.value
                new_pos = [sim_pos[0] + dx, sim_pos[1] + dy]
                if self.can_move(sim_pos, new_pos):
                    sim_pos = new_pos
        
        return sim_pos
    
    def move_enemies(self):
        """移動所有敵人"""
        for enemy in self.enemies:
            if enemy["stunned"] > 0:
                enemy["stunned"] -= 1
                continue
            
            # 移動 4 格
            for step in range(4):
                dx, dy = enemy["dir"].value
                new_pos = [enemy["pos"][0] + dx, enemy["pos"][1] + dy]
                
                if self.can_move(enemy["pos"], new_pos):
                    enemy["pos"] = new_pos
                else:
                    # 反彈 - 改變方向
                    if enemy["dir"] == Direction.RIGHT:
                        enemy["dir"] = Direction.LEFT
                    elif enemy["dir"] == Direction.LEFT:
                        enemy["dir"] = Direction.RIGHT
                    elif enemy["dir"] == Direction.UP:
                        enemy["dir"] = Direction.DOWN
                    else:
                        enemy["dir"] = Direction.UP
                    
                    # 反彈後用新方向移動
                    dx, dy = enemy["dir"].value
                    new_pos = [enemy["pos"][0] + dx, enemy["pos"][1] + dy]
                    if self.can_move(enemy["pos"], new_pos):
                        enemy["pos"] = new_pos
        
        self.update_doors()
    
    def use_skill1_on_enemy(self, enemy_index):
        """對敵人使用回溯技能"""
        if self.skill1_used_this_turn or self.skill1_uses <= 0:
            self.action_log.append("技能已使用或無剩餘次數")
            return False
        # 第一回合敵人還沒移動，不能回溯
        if self.turn_start_enemies is None:
            self.action_log.append("第一回合敵人還未移動，無法回溯！")
            self.selected_skill = None
            return False
        # 儲存使用技能前的狀態
        self.save_state()
        old_pos = self.enemies[enemy_index]["pos"].copy()
        start_pos = self.turn_start_enemies[enemy_index]["pos"].copy()
        # 添加調試信息
        self.action_log.append(f"嘗試回溯敵人 #{enemy_index+1}")
        self.action_log.append(f"當前位置：({old_pos[0]},{old_pos[1]})")
        self.action_log.append(f"回溯目標：({start_pos[0]},{start_pos[1]})")
        self.enemies[enemy_index]["pos"] = start_pos
        self.enemies[enemy_index]["dir"] = self.turn_start_enemies[enemy_index]["dir"]
        self.skill1_uses -= 1
        self.skill1_used_this_turn = True
        self.selected_skill = None
        self.update_doors()
        # 記錄行動
        self.action_log.append(f"回溯成功！")
        return True
    
    def use_skill1_on_player(self):
        """對玩家使用回溯技能"""
        if self.skill1_used_this_turn or self.skill1_uses <= 0:
            return False
        # 儲存使用技能前的狀態
        self.save_state()
        old_pos = self.player_pos.copy()
        self.player_pos = self.turn_start_player_pos.copy()
        self.skill1_uses -= 1
        self.skill1_used_this_turn = True
        self.selected_skill = None
        # 檢查黃色壓版狀態 (可能需要更新)
        self.update_doors()
        # 記錄行動
        self.action_log.append(f"回溯玩家：({old_pos[0]},{old_pos[1]}) → ({self.player_pos[0]},{self.player_pos[1]})")
        return True
    
    def use_skill2(self, center_x, center_y):
        """使用靜止技能"""
        if self.skill2_used_this_turn or self.skill2_uses <= 0:
            return False
        # 儲存使用技能前的狀態
        self.save_state()
        # 對 3x3 範圍內的所有敵人施加靜止效果
        stunned_any = False
        for enemy in self.enemies:
            ex, ey = enemy["pos"]
            if abs(ex - center_x) <= 1 and abs(ey - center_y) <= 1:
                enemy["stunned"] = 1  # 下一回合不能動
                stunned_any = True
        if stunned_any:
            self.skill2_uses -= 1
            self.skill2_used_this_turn = True
            self.selected_skill = None
            self.stun_area = None
            return True
        return False
    
    def end_turn(self):
        """結束當前回合，並儲存狀態以支援跨回合撤銷"""
        self.save_state()  # 儲存回合結束前的狀態
        if self.is_first_turn:
            # 第一回合結束
            self.is_first_turn = False
            self.turn += 1
            self.player_moves_left = 6
            self.skill1_used_this_turn = False
            self.skill2_used_this_turn = False
            self.selected_skill = None
            self.player_turn = False
            self.action_log = []  # 清空行動記錄
            # 記錄敵人移動前的狀態 (下一回合可以回溯到這裡)
            self.turn_start_enemies = deepcopy(self.enemies)
            # 敵人自動移動
            self.move_enemies()
            # 記錄玩家位置 (玩家還沒移動)
            self.turn_start_player_pos = self.player_pos.copy()
            self.player_turn = True
        else:
            # 正常回合結束
            self.turn += 1
            if self.turn > self.max_turns:
                self.game_lost = True
                return
            self.player_moves_left = 6
            self.skill1_used_this_turn = False
            self.skill2_used_this_turn = False
            self.selected_skill = None
            self.player_turn = False
            self.action_log = []  # 清空行動記錄
            # 記錄敵人移動前的狀態 (下一回合可以回溯到這裡)
            self.turn_start_enemies = deepcopy(self.enemies)
            # 敵人自動移動
            self.move_enemies()
            # 記錄玩家位置 (玩家還沒移動)
            self.turn_start_player_pos = self.player_pos.copy()
            self.player_turn = True
    
    def handle_click(self, pos):
        """處理點擊事件"""
        mouse_x, mouse_y = pos
        
        # 檢查側邊欄按鈕
        if mouse_x >= GRID_SIZE * CELL_SIZE:
            # 勝利或失敗時，僅允許重新開始
            if self.game_won or self.game_lost:
                if hasattr(self, 'restart_button') and self.restart_button.collidepoint(pos):
                    self.init_game()
                    self.action_log.append("遊戲已重新開始")
                return
            if hasattr(self, 'skill1_button') and self.skill1_button.collidepoint(pos):
                if self.skill1_uses > 0 and not self.skill1_used_this_turn:
                    self.selected_skill = 'skill1' if self.selected_skill != 'skill1' else None
            elif hasattr(self, 'skill2_button') and self.skill2_button.collidepoint(pos):
                if self.skill2_uses > 0 and not self.skill2_used_this_turn:
                    self.selected_skill = 'skill2' if self.selected_skill != 'skill2' else None
                    if self.selected_skill == 'skill2':
                        self.stun_area = None
            elif hasattr(self, 'undo_button') and self.undo_button.collidepoint(pos):
                self.undo()
            elif hasattr(self, 'redo_button') and self.redo_button.collidepoint(pos):
                self.redo()
            elif hasattr(self, 'end_turn_button') and self.end_turn_button.collidepoint(pos):
                self.end_turn()
            elif hasattr(self, 'restart_button') and self.restart_button.collidepoint(pos):
                self.init_game()
                self.action_log.append("遊戲已重新開始")
            return
        
        # 遊戲區域點擊
        if mouse_x < GRID_SIZE * CELL_SIZE:
            click_x, click_y = self.screen_to_coord(mouse_x, mouse_y)
            if self.selected_skill == 'skill1':
                self.action_log.append(f"點擊位置：({click_x},{click_y})")
                # 檢查是否點擊玩家
                if self.player_pos == [click_x, click_y]:
                    self.action_log.append("點擊到玩家")
                    self.use_skill1_on_player()
                else:
                    # 檢查是否點擊敵人
                    found_enemy = False
                    for i, enemy in enumerate(self.enemies):
                        if enemy["pos"] == [click_x, click_y]:
                            self.action_log.append(f"點擊到敵人 #{i+1}")
                            self.use_skill1_on_enemy(i)
                            found_enemy = True
                            break
                    if not found_enemy:
                        self.action_log.append("沒有點擊到任何單位")
            elif self.selected_skill == 'skill2':
                # 預覽靜止範圍
                self.stun_area = (click_x, click_y)
                # 實際使用技能（不論有無敵人都可施放）
                self.use_skill2(click_x, click_y)
    
    def run(self):
        """遊戲主循環"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # 左鍵
                        self.handle_click(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    # 靜止技能預覽：滑鼠移動時即時顯示範圍
                    if self.selected_skill == 'skill2' and self.player_turn and not self.game_won and not self.game_lost:
                        mx, my = event.pos
                        if mx < GRID_SIZE * CELL_SIZE:
                            cx, cy = self.screen_to_coord(mx, my)
                            self.stun_area = (cx, cy)
                        else:
                            self.stun_area = None
                elif event.type == pygame.KEYDOWN:
                    if self.player_turn and not self.game_won and not self.game_lost:
                        if event.key in (pygame.K_w, pygame.K_UP):
                            self.move_player(0, 1)
                        elif event.key in (pygame.K_s, pygame.K_DOWN):
                            self.move_player(0, -1)
                        elif event.key in (pygame.K_a, pygame.K_LEFT):
                            self.move_player(-1, 0)
                        elif event.key in (pygame.K_d, pygame.K_RIGHT):
                            self.move_player(1, 0)
            # 繪製
            self.screen.fill(WHITE)
            self.draw_grid()
            self.draw_sidebar()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
