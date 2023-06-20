import unittest
import game_networks_socketutil
import game_network_server
import time
from datatypes import *
import json
from queue import Queue

import game_networks as game_networks_1
import game_networks as game_networks_2

class Testing(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        game_networks_1.init(Queue(), Queue())
        game_networks_2.init(Queue(), Queue())
        cls.serverSock,_,_ = game_networks_socketutil.openServerSocket(game_network_server.handler, "0.0.0.0", 0)
        game_networks_1.ip = cls.serverSock.getsockname()[0]
        game_networks_1.port = cls.serverSock.getsockname()[1]
        game_networks_2.ip = cls.serverSock.getsockname()[0]
        game_networks_2.port = cls.serverSock.getsockname()[1]
        return super().setUpClass()
    
    @classmethod
    def tearDownClass(cls) -> None:
        game_networks_socketutil.closeall([])
        return super().tearDownClass()
    
    def test_availablegames(self):
        game_networks_1.requestAvailableGames()
        event = game_networks_1.mainQueue.get()
        print(f"{event.getType()}")
        game_networks_1.mainQueue.task_done()
        self.assertEqual(event, Event("LIST", json.loads("[]")))

    def test_new(self):
        self.test_availablegames()

        # Create a new game and get ID
        game_networks_1.newGame()
        self.id = game_networks_1.mainQueue.get().getData()
        game_networks_1.mainQueue.task_done()

        # Verify valid room number was chosen
        self.assertEqual(type(self.id), int)
        self.assertTrue(self.id > 99999 and self.id < 1000000)
    
    def test_new_list(self):
        self.test_new()

        # Verify valid room was created
        game_networks_1.requestAvailableGames()
        event = game_networks_1.mainQueue.get()
        game_networks_1.mainQueue.task_done()
        self.assertEqual(event, Event("PLAYERS", json.loads(f"[{{\"id\": {self.id}, \"players\": 1}}]")))

    def test_join(self):
        self.test_new()
        game_networks_2.requestAvailableGames()
        gamejson = game_networks_2.mainQueue.get().getData()
        game_networks_2.mainQueue.task_done()
        id1 = gamejson[0]["id"]
        game_networks_2.joinGame(id1)
        id2 = game_networks_2.mainQueue.get().getData()
        game_networks_2.mainQueue.task_done()
        self.assertEqual(id1, id2)
    
    def test_start(self):
        self.test_new()
        game_networks_1.startGame()
        event = game_networks_1.mainQueue.get()
        game_networks_1.mainQueue.task_done()
        print(f"Event: {event.toString()}")
        game_networks_1.stopGame()
        self.assertEqual(event.getType(), "START")
    
