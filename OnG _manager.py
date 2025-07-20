import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
import random
import numpy as np
import time
from stable_baselines3.common.callbacks import EvalCallback
import random
import pygame
import sys

class OilnGas(gym.Env):
    def __init__(self,para=None):
        super(OilnGas, self).__init__()
        self.max_per_order = 20
        self.observation_space = spaces.Box(low=0, high=100000,shape=(10,), dtype=np.float32)
        self.action_space = spaces.Discrete(self.max_per_order+1)


    def reset(self, *,seed=None, options = None):
        super().reset()
        #parameter
        self.current_day = 1
        self.day_counter = 0
        self.max_inventory = 40
        self.daily_use = 3
        self.ship_cost = random.uniform(900,1000)
        self.storage_cost = 3
        self.lead_time = 2
        self.arrive_next_day = 0
        self.pending = []
        self.cost_each_week = []
        self.cum_perweek = 0
        self.cum_permonth = 0
        self.current_inventory = 12
        self.budget = 2000

        print(f"""
        Daily Use: {self.daily_use}
        Ship Cost: {self.ship_cost}
        Storage : {self.storage_cost}
        Budget: {self.budget}
        """)
        print("-"*50)


        environment = [
            self.current_day,
            self.max_inventory,
            self.daily_use, 
            self.ship_cost,
            self.storage_cost,
            self.lead_time,
            self.arrive_next_day,
            self.cum_perweek,
            self.current_inventory,
            self.day_counter
            ]
        
        obs = np.array(environment,dtype=np.float32).flatten()
        return obs,{}

    def step(self, action):
        reward = 0
        terminated = False
        truncated = False
        info = {}
        action = int(action)
        if self.pending:
            for index,arrive in enumerate(self.pending):
                if arrive[0] == self.current_day:
                    self.current_inventory += arrive[1]
                    if self.current_inventory > 40:
                        self.current_inventory = 40
                        #r
                        reward -= 10
                    try:
                        self.pending.pop(index)
                    except IndexError:
                        print("Error")
                
                if arrive[0] == self.current_day+1 and self.current_day != 7:
                    self.arrive_next_day = arrive[1]
        else:
            self.arrive_next_day = 0
            
        if action != 0:

            if self.current_day+self.lead_time <= 7:
                self.pending.append((self.current_day+self.lead_time,action))
            else:
                self.pending.append(((self.current_day+self.lead_time)-7,action))
        
        #Cost Cumulate
        if self.current_inventory != 0:
            self.cum_perweek += self.current_inventory * self.storage_cost
            self.cum_permonth += self.current_inventory * self.storage_cost
            #r
        if action != 0:
            self.cum_perweek += 1000
            self.cum_permonth += 1000

        else:
            reward += 5
        
        #Operation
        if self.current_inventory < 4:
            #r
            reward -= 25
            self.cum_perweek += 10000
            self.cum_permonth += 10000
            # terminated = True
        else:
            self.current_inventory -= self.daily_use
            #r
            

        #Update environment
        if self.day_counter < 30:
            if self.current_day == 7:
                
                if self.cost_each_week:
                    if self.cum_perweek < self.budget:
                        reward += 10
                    else:
                        reward -= 2
                    # if self.cum_perweek > self.cost_each_week[-1]:
                    #     #r
                    #     reward -= 1
                        
                    # else:
                    #     #r
                    #     reward += 3 
                self.cost_each_week.append(self.cum_perweek)
                self.cum_perweek = 0
                self.current_day = 1
            else:
                self.current_day += 1
            
            self.day_counter += 1
        else:
            terminated = True

        environment = [
            self.current_day,
            self.max_inventory,
            self.daily_use, 
            self.ship_cost,
            self.storage_cost,
            self.lead_time,
            self.arrive_next_day,
            self.cum_perweek,
            self.current_inventory,
            self.day_counter
            ]
        
        obs = np.array(environment,dtype=np.float32).flatten()

        return obs, reward, terminated, truncated, info


    def printenv(self):
        print("-"*50)
        print(f"""
        Current Day: {self.current_day}
        Arrive Next Day: {self.arrive_next_day}
        Cumulative per Week: {self.cum_perweek}
        Current Inventory: {self.current_inventory}
        Pending: {self.pending}
        Day Counter: {self.day_counter}
        Budget: {self.budget}
        """)
        print("-"*50)

    def printmonth(self):
        print(f"Cumulative per Month: {self.cum_permonth}\nPer Week:{self.cost_each_week}")


class Ship():
    def __init__(self):
        self.x = 0
        self.y = 230
        self.count = 0
        self.ship = pygame.image.load("lib/ship.png").convert_alpha()
        self.ship = pygame.transform.scale_by(self.ship,0.4)
    
    def Move(self):
        self.x += 150
        self.count += 1

    def draw(self,screen):
        screen.blit(self.ship,(self.x,self.y))

if __name__ == "__main__":
    
    env = OilnGas()
    check_env(env)
    training = False
    running = True

    pygame.init()
    screen = pygame.display.set_mode((800,600))
    clock = pygame.time.Clock()
    WHITE = (255, 255, 255)


    background = pygame.image.load("lib/bg.png").convert()
    background = pygame.transform.scale(background, (800, 600))
    rig = pygame.image.load("lib/oilrig.png").convert_alpha()
    rig = pygame.transform.scale_by(rig,0.6)
    font = pygame.font.SysFont('arial', 20)

    # rig = pygame.transform.scale_by(rig,0.6)
    

    infolist = [0,0,0,0]
    riginfo = f"Current Inventory: {infolist[0]}\nTotal Cost: RM{infolist[1]}\nDaily Usage: {infolist[2]}\nArrive Next Day: {infolist[3]}"
    day_counter = font.render(f"Day {env.current_day}", True, (0, 0, 0))
    lines = riginfo.split('\n')
    list_ship = []

    if training:
        model = PPO("MlpPolicy", env, verbose=1)
        eval_callback = EvalCallback(env, best_model_save_path="./logs/",
                             log_path="./logs/", eval_freq=500,
                             deterministic=True, render=False)
        model.learn(total_timesteps=500000)
        model.save("Inventory_managerv9")
    else:
        model = PPO.load("Model/NO1.2.zip")
        done = False
        obs, _ = env.reset()

        robot = pygame.image.load("lib/robot2.png").convert_alpha()


        while running or done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            action, _ = model.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            if done:
                running = False

            # Update info
            robot_text = f"Order Placed by Robot: {action}"
            robot_render = font.render(robot_text,True, (0, 0, 0))
            infolist[0] = env.current_inventory
            infolist[1] = env.cum_permonth
            infolist[2] = env.daily_use
            infolist[3] = env.arrive_next_day
            riginfo = f"Current Inventory: {infolist[0]}\nTotal Cost: {infolist[1]}\nDaily Usage: {infolist[2]}\nArrive Next Day: {infolist[3]}"
            lines = riginfo.split('\n')
            day_counter = font.render(f"Day {env.day_counter}", True, (0, 0, 0))

            # Draw screen
            screen.blit(background, (0, 0))
            screen.blit(rig, (600, 150))
            screen.blit(robot, (50, 50))
            screen.blit(robot_render, (150, 100))

            y = 50
            for line in lines:
                text_surface = font.render(line, True, (0, 0, 0))
                screen.blit(text_surface, (550, y))
                y += font.get_linesize()

            screen.blit(day_counter, (150, 50))
        

            if action != 0:
                list_ship.append(Ship())
            
            for ship in list_ship:
                if ship.count <= 2:
                    ship.Move()
                    ship.draw(screen)

            list_ship = [s for s in list_ship if s.x <= 450]

            pygame.display.flip()
            clock.tick(60)
            time.sleep(1)

            env.printenv()
            print(f"Action: {action}, Reward: {reward}, Done: {done}")

        env.printmonth()
        pygame.quit()
        sys.exit()

