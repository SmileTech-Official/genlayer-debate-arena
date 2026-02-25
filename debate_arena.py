# { "Depends": "py-genlayer:test" }

from genlayer import *
import json

class DebateArena(gl.Contract):
    debates_data: str
    player_xp_data: str
    
    def __init__(self):
        self.debates_data = "{}"
        self.player_xp_data = "{}"
    
    @gl.public.write
    def create_debate(self, topic: str) -> str:
        """Create a new debate"""
        import time
        debate_id = f"{int(time.time())}_{topic[:30].replace(' ', '_')}"
        
        # Load existing debates
        debates = json.loads(self.debates_data)
        
        # Create new debate
        debates[debate_id] = {
            "topic": topic,
            "pro_args": [],
            "con_args": [],
            "status": "open",
            "winner": "",
            "confidence": 0
        }
        
        # Save back
        self.debates_data = json.dumps(debates)
        
        return debate_id
    
    @gl.public.write
    def submit_argument(self, debate_id: str, side: str, argument: str) -> str:
        """Submit an argument to a debate"""
        debates = json.loads(self.debates_data)
        
        if debate_id not in debates:
            return "Error: Debate not found"
        
        debate = debates[debate_id]
        
        if debate["status"] != "open":
            return "Error: Debate is closed"
        
        new_arg = {
            "player": str(self.sender),
            "text": argument
        }
        
        if side.lower() == "pro":
            debate["pro_args"].append(new_arg)
        elif side.lower() == "con":
            debate["con_args"].append(new_arg)
        else:
            return "Error: Side must be 'pro' or 'con'"
        
        self.debates_data = json.dumps(debates)
        return "Argument submitted successfully"
    
    @gl.public.write
    def resolve_debate(self, debate_id: str) -> dict:
        """Use AI to judge the debate"""
        debates = json.loads(self.debates_data)
        
        if debate_id not in debates:
            return {"error": "Debate not found"}
        
        debate = debates[debate_id]
        
        if debate["status"] != "open":
            return {"error": "Already resolved"}
        
        # Build arguments text
        pro_text = "\n".join([arg["text"] for arg in debate["pro_args"]])
        con_text = "\n".join([arg["text"] for arg in debate["con_args"]])
        
        # Create AI prompt
        prompt = f"""
You are a fair debate judge.

TOPIC: {debate["topic"]}

PRO ARGUMENTS:
{pro_text if pro_text else "No arguments"}

CON ARGUMENTS:
{con_text if con_text else "No arguments"}

Judge based on logic, evidence, and persuasiveness.

Respond ONLY in this JSON format:
{{
  "winner": "pro" or "con",
  "confidence": 75,
  "reason": "brief explanation"
}}
"""
        
        # Call AI
        raw_result = llm_prompt(prompt, model="balanced")
        
        # Parse result
        try:
            result = json.loads(raw_result)
            winner = result["winner"].lower()
            confidence = int(result["confidence"])
            reason = result.get("reason", "")
        except:
            winner = "tie"
            confidence = 0
            reason = "Parsing failed"
        
        if winner not in ["pro", "con"]:
            winner = "tie"
        
        # Update debate
        debate["winner"] = winner
        debate["confidence"] = confidence
        debate["status"] = "resolved"
        
        # Award XP
        if winner != "tie":
            player_xp = json.loads(self.player_xp_data)
            winning_args = debate["pro_args"] if winner == "pro" else debate["con_args"]
            xp_per_player = 10 + (confidence // 10)
            
            for arg in winning_args:
                player = arg["player"]
                current_xp = player_xp.get(player, 0)
                player_xp[player] = current_xp + xp_per_player
            
            self.player_xp_data = json.dumps(player_xp)
        
        self.debates_data = json.dumps(debates)
        
        return {
            "winner": winner,
            "confidence": confidence,
            "reason": reason
        }
    
    @gl.public.view
    def get_debate(self, debate_id: str) -> dict:
        """Get debate information"""
        debates = json.loads(self.debates_data)
        
        if debate_id not in debates:
            return {"error": "Not found"}
        
        return debates[debate_id]
    
    @gl.public.view
    def get_player_xp(self, player: str) -> int:
        """Get player's XP"""
        player_xp = json.loads(self.player_xp_data)
        return player_xp.get(player, 0)
