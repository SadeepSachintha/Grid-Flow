import hashlib
import math
import random
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

class VppTradingEngine:
    """
    Virtual Power Plant (VPP) Aggregation & Peer-to-Peer (P2P) Microgrid Energy Trading Engine.
    Aggregates Solaria West (25 MW Solar/Wind/BESS) with regional industrial prosumers:
      1. Solaria West (Anchor 25.0 MW Solar/Wind/BESS)
      2. Mojave Green Hydrogen Electrolyzer (8.0 MW flexible PEM electrolyzer)
      3. Boron Lithium Processing Facility (6.5 MW baseload industrial load)
      4. Mojave Compute AI Data Center (4.0 MW IT load with 1.5 MW curtailable batch compute)

    Features:
      - Continuous Double-Auction & Merit-Order Clearing
      - Locational Marginal Pricing (LMP) with line congestion & loss factors
      - P2P Bilateral Contract Settlement
      - Cryptographic Renewable Energy Certificate (REC) Token Minting (SHA-256)
      - Carbon Avoidance Accounting (0.385 tCO2/MWh)
    """

    def __init__(self):
        # Static Asset Specifications
        self.assets: Dict[str, Dict[str, Any]] = {
            "SOLARIA_WEST": {
                "id": "SOLARIA_WEST",
                "name": "Solaria West Microgrid",
                "type": "PROSUMER_HYBRID",
                "capacity_mw": 25.0,
                "current_power_mw": 18.5,
                "is_generation": True,
                "status": "ONLINE",
                "marginal_cost_mwh": 14.50, # Levelized OPEX
                "feeder_congestion_mw": 0.0,
                "loss_factor": 0.012,
                "lmp_usd_mwh": 32.40,
                "description": "20 MW Solar PV + 5 MW Wind + 10 MWh BESS"
            },
            "MOJAVE_H2": {
                "id": "MOJAVE_H2",
                "name": "Mojave Green H2 Electrolyzer",
                "type": "FLEXIBLE_LOAD",
                "capacity_mw": 8.0,
                "current_power_mw": 4.8,
                "is_generation": False,
                "status": "ONLINE",
                "h2_storage_pct": 62.5,
                "min_operating_mw": 2.0,
                "max_operating_mw": 8.0,
                "marginal_bid_mwh": 36.00,
                "feeder_congestion_mw": 0.0,
                "loss_factor": 0.018,
                "lmp_usd_mwh": 33.10,
                "description": "8.0 MW PEM Electrolyzer with 12h H2 Buffer"
            },
            "BORON_LITHIUM": {
                "id": "BORON_LITHIUM",
                "name": "Boron Lithium Refining",
                "type": "CRITICAL_INDUSTRIAL",
                "capacity_mw": 6.5,
                "current_power_mw": 6.2,
                "is_generation": False,
                "status": "ONLINE",
                "min_operating_mw": 5.5,
                "max_operating_mw": 6.5,
                "marginal_bid_mwh": 95.00, # High willingness to pay to prevent refinery shutdown
                "feeder_congestion_mw": 1.2, # Feeder 3 experiences thermal bottleneck
                "loss_factor": 0.024,
                "lmp_usd_mwh": 38.60,
                "description": "6.5 MW Continuous Chemical Extraction & Refining"
            },
            "MOJAVE_COMPUTE": {
                "id": "MOJAVE_COMPUTE",
                "name": "Mojave Compute AI Center",
                "type": "CURTAILABLE_COMPUTE",
                "capacity_mw": 4.0,
                "current_power_mw": 3.8,
                "is_generation": False,
                "status": "ONLINE",
                "critical_load_mw": 2.5, # Critical cooling + live inference
                "batch_load_mw": 1.5,    # Curtailable training clusters
                "curtailed": False,
                "marginal_bid_mwh": 82.00,
                "feeder_congestion_mw": 0.0,
                "loss_factor": 0.028,
                "lmp_usd_mwh": 34.20,
                "description": "4.0 MW AI Data Center (1.5 MW Curtailable Workloads)"
            }
        }

        # Market State
        self.market_clearing_price_usd_mwh = 34.50
        self.cleared_volume_mw = 14.8
        self.consumer_surplus_usd = 425.80
        self.producer_surplus_usd = 296.40
        self.total_energy_traded_mwh = 184.20
        self.total_carbon_avoided_tons = 70.92
        self.active_order_book: Dict[str, List[Dict[str, Any]]] = {
            "bids": [],
            "asks": []
        }
        self.recent_transactions: List[Dict[str, Any]] = []
        self.minted_rec_tokens: List[Dict[str, Any]] = []

        # Market event overrides
        self.event_overrides: Dict[str, Any] = {
            "electrolyzer_surge": False,
            "datacenter_curtailment": False,
            "peak_arbitrage": False
        }

        # Seed initial order book and transactions
        self._seed_initial_history()

    def _seed_initial_history(self):
        """Seed a realistic initial ledger of recent P2P bilateral trades with cryptographic REC hashes."""
        past_trades = [
            ("MOJAVE_H2", "SOLARIA_WEST", 4.5, 32.80, "2026-09-21T11:45:00Z"),
            ("BORON_LITHIUM", "SOLARIA_WEST", 6.2, 35.40, "2026-09-21T11:50:00Z"),
            ("MOJAVE_COMPUTE", "SOLARIA_WEST", 3.8, 34.10, "2026-09-21T11:55:00Z"),
            ("MOJAVE_H2", "SOLARIA_WEST", 5.0, 33.20, "2026-09-21T12:00:00Z"),
            ("BORON_LITHIUM", "SOLARIA_WEST", 6.0, 36.50, "2026-09-21T12:05:00Z"),
        ]
        for buyer, seller, mw, price, ts in past_trades:
            self._record_transaction(buyer, seller, mw, price, ts)

    def _generate_rec_token(self, trade_id: str, seller_id: str, buyer_id: str, mwh: float, timestamp: str) -> Dict[str, Any]:
        """Mint a cryptographic Renewable Energy Certificate (REC) Token using SHA-256."""
        raw_payload = f"{trade_id}:{seller_id}:{buyer_id}:{mwh:.4f}:{timestamp}:VPP_SOLARIA_WEST_ORIGIN"
        sha_hash = "0x" + hashlib.sha256(raw_payload.encode()).hexdigest()
        co2_tons = round(mwh * 0.385, 3) # 0.385 metric tons CO2 avoided per MWh vs CAISO marginal gas peaker
        
        return {
            "token_id": f"REC-{trade_id[-6:]}",
            "trade_id": trade_id,
            "seller_id": seller_id,
            "buyer_id": buyer_id,
            "volume_mwh": round(mwh, 3),
            "co2_avoided_tons": co2_tons,
            "hash_proof": sha_hash,
            "minted_at": timestamp,
            "standard": "GHG-Scope-2 / WREGIS-Compatible"
        }

    def _record_transaction(self, buyer_id: str, seller_id: str, mw: float, price: float, timestamp: str) -> Dict[str, Any]:
        trade_id = f"TX-VPP-{random.randint(100000, 999999)}"
        mwh = round(mw * (2.0 / 3600.0), 4) # 2-second trading interval
        if mwh <= 0.0001:
            mwh = round(mw * 0.25, 4) # Default 15-min settlement frame equivalent for realism
        
        token = self._generate_rec_token(trade_id, seller_id, buyer_id, mwh, timestamp)
        self.minted_rec_tokens.append(token)
        if len(self.minted_rec_tokens) > 50:
            self.minted_rec_tokens.pop(0)

        tx = {
            "trade_id": trade_id,
            "buyer_id": buyer_id,
            "buyer_name": self.assets[buyer_id]["name"],
            "seller_id": seller_id,
            "seller_name": self.assets[seller_id]["name"],
            "cleared_mw": round(mw, 2),
            "cleared_price_mwh": round(price, 2),
            "total_settlement_usd": round(mw * price, 2),
            "rec_token": token,
            "timestamp": timestamp
        }
        self.recent_transactions.insert(0, tx)
        if len(self.recent_transactions) > 30:
            self.recent_transactions.pop()
            
        self.total_energy_traded_mwh += mwh
        self.total_carbon_avoided_tons += token["co2_avoided_tons"]
        return tx

    def trigger_electrolyzer_surge(self, extra_mw: float = 3.2, max_bid: float = 48.0):
        """Mojave H2 ramps up to absorb peak green hydrogen production."""
        self.event_overrides["electrolyzer_surge"] = True
        self.assets["MOJAVE_H2"]["current_power_mw"] = min(8.0, 4.8 + extra_mw)
        self.assets["MOJAVE_H2"]["marginal_bid_mwh"] = max_bid

    def trigger_datacenter_curtailment(self, shed_mw: float = 1.5):
        """Mojave Compute sheds flexible batch compute jobs in response to market signals."""
        self.event_overrides["datacenter_curtailment"] = True
        self.assets["MOJAVE_COMPUTE"]["curtailed"] = True
        self.assets["MOJAVE_COMPUTE"]["current_power_mw"] = max(2.5, 4.0 - shed_mw)

    def trigger_peak_arbitrage(self, discharge_mw: float = 4.0, ask_price: float = 110.0):
        """Solaria West BESS enters peak arbitrage mode with a high ask price."""
        self.event_overrides["peak_arbitrage"] = True

    def reset_market(self):
        """Reset all market overrides and return to standard operating conditions."""
        self.event_overrides = {
            "electrolyzer_surge": False,
            "datacenter_curtailment": False,
            "peak_arbitrage": False
        }
        self.assets["MOJAVE_H2"]["current_power_mw"] = 4.8
        self.assets["MOJAVE_H2"]["marginal_bid_mwh"] = 36.00
        self.assets["MOJAVE_COMPUTE"]["curtailed"] = False
        self.assets["MOJAVE_COMPUTE"]["current_power_mw"] = 3.8
        self.assets["MOJAVE_COMPUTE"]["marginal_bid_mwh"] = 82.00

    def update(self, total_renewable_kw: float, bess_dispatch_kw: float, bess_soc_pct: float, dt_seconds: float = 2.0) -> Dict[str, Any]:
        """
        Execute continuous double-auction clearing and update VPP asset states.
        Called every 2-second simulation tick.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # 1. Update Solaria West Generation & Available Power
        solaria_gen_mw = total_renewable_kw / 1000.0
        bess_mw = bess_dispatch_kw / 1000.0
        solaria_export_available_mw = max(0.0, solaria_gen_mw + bess_mw)
        self.assets["SOLARIA_WEST"]["current_power_mw"] = round(solaria_export_available_mw, 2)
        
        # Solaria West marginal cost varies slightly by solar vs wind vs BESS
        if bess_mw > 0.5:
            # Discharging battery has degradation cost (~$22/MWh) + baseline
            base_ask = 36.50
        else:
            base_ask = 14.50 + random.uniform(-0.5, 0.5)
            
        if self.event_overrides["peak_arbitrage"]:
            base_ask = 92.00

        # 2. Update Demand Nodes
        # Electrolyzer adjusts based on H2 tank level
        if not self.event_overrides["electrolyzer_surge"]:
            h2_tank = self.assets["MOJAVE_H2"]["h2_storage_pct"]
            if h2_tank > 90.0:
                self.assets["MOJAVE_H2"]["current_power_mw"] = 2.5 # Fill rate slowed
                self.assets["MOJAVE_H2"]["marginal_bid_mwh"] = 22.00
            elif h2_tank < 40.0:
                self.assets["MOJAVE_H2"]["current_power_mw"] = 6.5
                self.assets["MOJAVE_H2"]["marginal_bid_mwh"] = 44.00
            else:
                self.assets["MOJAVE_H2"]["current_power_mw"] = 4.8 + random.uniform(-0.2, 0.2)
                self.assets["MOJAVE_H2"]["marginal_bid_mwh"] = 36.00 + random.uniform(-1.0, 1.0)
                
            # Slowly fluctuate H2 tank
            self.assets["MOJAVE_H2"]["h2_storage_pct"] = min(100.0, max(15.0, h2_tank + 0.015))

        # Boron Lithium continuous load with minor noise
        boron_load = 6.2 + random.uniform(-0.15, 0.15)
        self.assets["BORON_LITHIUM"]["current_power_mw"] = round(boron_load, 2)

        # Mojave Compute load
        if not self.event_overrides["datacenter_curtailment"]:
            compute_load = 3.8 + random.uniform(-0.1, 0.1)
            self.assets["MOJAVE_COMPUTE"]["current_power_mw"] = round(compute_load, 2)

        # 3. Construct Order Book
        bids = [
            {
                "bid_id": "BID-BORON-01",
                "node_id": "BORON_LITHIUM",
                "node_name": self.assets["BORON_LITHIUM"]["name"],
                "mw": round(self.assets["BORON_LITHIUM"]["current_power_mw"], 2),
                "price_usd_mwh": round(self.assets["BORON_LITHIUM"]["marginal_bid_mwh"], 2),
                "priority": "HIGH_UNINTERRUPTIBLE"
            },
            {
                "bid_id": "BID-COMPUTE-01",
                "node_id": "MOJAVE_COMPUTE",
                "node_name": self.assets["MOJAVE_COMPUTE"]["name"],
                "mw": round(2.5, 2), # Critical IT
                "price_usd_mwh": round(self.assets["MOJAVE_COMPUTE"]["marginal_bid_mwh"], 2),
                "priority": "CRITICAL"
            }
        ]
        
        if not self.assets["MOJAVE_COMPUTE"]["curtailed"]:
            bids.append({
                "bid_id": "BID-COMPUTE-02",
                "node_id": "MOJAVE_COMPUTE",
                "node_name": self.assets["MOJAVE_COMPUTE"]["name"],
                "mw": round(self.assets["MOJAVE_COMPUTE"]["current_power_mw"] - 2.5, 2),
                "price_usd_mwh": 55.00,
                "priority": "CURTAILABLE_BATCH"
            })

        bids.append({
            "bid_id": "BID-H2-01",
            "node_id": "MOJAVE_H2",
            "node_name": self.assets["MOJAVE_H2"]["name"],
            "mw": round(self.assets["MOJAVE_H2"]["current_power_mw"], 2),
            "price_usd_mwh": round(self.assets["MOJAVE_H2"]["marginal_bid_mwh"], 2),
            "priority": "FLEXIBLE_DISPATCH"
        })

        asks = [
            {
                "ask_id": "ASK-SOLARIA-PV",
                "node_id": "SOLARIA_WEST",
                "node_name": "Solaria West Solar/Wind",
                "mw": round(min(solaria_export_available_mw, 16.0), 2),
                "price_usd_mwh": round(base_ask, 2),
                "source": "DIRECT_RENEWABLE"
            }
        ]
        
        if solaria_export_available_mw > 16.0:
            asks.append({
                "ask_id": "ASK-SOLARIA-BESS",
                "node_id": "SOLARIA_WEST",
                "node_name": "Solaria West BESS Buffer",
                "mw": round(solaria_export_available_mw - 16.0, 2),
                "price_usd_mwh": round(base_ask + 8.50, 2),
                "source": "BESS_STORAGE"
            })

        # Sort Bids descending (highest willingness to pay first)
        bids_sorted = sorted(bids, key=lambda x: x["price_usd_mwh"], reverse=True)
        # Sort Asks ascending (lowest cost first)
        asks_sorted = sorted(asks, key=lambda x: x["price_usd_mwh"])

        # 4. Continuous Double-Auction Merit-Order Clearing
        cleared_trades, mcp, total_cleared_mw, cons_surplus, prod_surplus = self._clear_market(bids_sorted, asks_sorted)
        
        self.market_clearing_price_usd_mwh = round(mcp, 2)
        self.cleared_volume_mw = round(total_cleared_mw, 2)
        self.consumer_surplus_usd = round(cons_surplus, 2)
        self.producer_surplus_usd = round(prod_surplus, 2)
        self.active_order_book = {
            "bids": bids_sorted,
            "asks": asks_sorted
        }

        # Record top bilateral transaction if clearing occurred
        if cleared_trades:
            top_trade = cleared_trades[0]
            self._record_transaction(
                buyer_id=top_trade["buyer_id"],
                seller_id=top_trade["seller_id"],
                mw=top_trade["mw"],
                price=self.market_clearing_price_usd_mwh,
                timestamp=now_iso
            )

        # 5. Compute Nodal LMPs (Energy + Congestion + Losses)
        for asset_id, asset in self.assets.items():
            congestion_cost = asset["feeder_congestion_mw"] * 3.50 # $3.50 per congested MW
            loss_cost = mcp * asset["loss_factor"]
            asset["lmp_usd_mwh"] = round(mcp + congestion_cost + loss_cost, 2)

        # 6. Aggregate Metrics
        total_gen_mw = sum(a["current_power_mw"] for a in self.assets.values() if a["is_generation"])
        total_load_mw = sum(a["current_power_mw"] for a in self.assets.values() if not a["is_generation"])
        net_balance_mw = round(total_gen_mw - total_load_mw, 2)

        return {
            "market_clearing_price_usd_mwh": self.market_clearing_price_usd_mwh,
            "cleared_volume_mw": self.cleared_volume_mw,
            "total_gen_mw": round(total_gen_mw, 2),
            "total_load_mw": round(total_load_mw, 2),
            "net_balance_mw": net_balance_mw,
            "consumer_surplus_usd": self.consumer_surplus_usd,
            "producer_surplus_usd": self.producer_surplus_usd,
            "total_energy_traded_mwh": round(self.total_energy_traded_mwh, 2),
            "total_carbon_avoided_tons": round(self.total_carbon_avoided_tons, 2),
            "assets": list(self.assets.values()),
            "order_book": self.active_order_book,
            "recent_transactions": self.recent_transactions[:10],
            "latest_rec_token": self.minted_rec_tokens[-1] if self.minted_rec_tokens else None,
            "event_overrides": self.event_overrides
        }

    def _clear_market(self, bids: List[Dict[str, Any]], asks: List[Dict[str, Any]]):
        """
        Merit-Order Double Auction Clearing Algorithm.
        Finds the uniform clearing price where supply meets demand.
        """
        if not bids or not asks:
            return [], 32.00, 0.0, 0.0, 0.0

        b_idx = 0
        s_idx = 0
        cleared_trades = []
        total_mw = 0.0
        last_cleared_bid = bids[0]["price_usd_mwh"]
        last_cleared_ask = asks[0]["price_usd_mwh"]

        # Create mutable copies of quantities
        remaining_bids = [{"id": b["node_id"], "mw": b["mw"], "price": b["price_usd_mwh"]} for b in bids]
        remaining_asks = [{"id": a["node_id"], "mw": a["mw"], "price": a["price_usd_mwh"]} for a in asks]

        while b_idx < len(remaining_bids) and s_idx < len(remaining_asks):
            cur_bid = remaining_bids[b_idx]
            cur_ask = remaining_asks[s_idx]

            # Clearing condition: Bid price >= Ask price
            if cur_bid["price"] >= cur_ask["price"]:
                matched_mw = min(cur_bid["mw"], cur_ask["mw"])
                if matched_mw > 0.01:
                    cleared_trades.append({
                        "buyer_id": cur_bid["id"],
                        "seller_id": cur_ask["id"],
                        "mw": round(matched_mw, 2),
                        "bid_price": cur_bid["price"],
                        "ask_price": cur_ask["price"]
                    })
                    total_mw += matched_mw
                    last_cleared_bid = cur_bid["price"]
                    last_cleared_ask = cur_ask["price"]

                    cur_bid["mw"] -= matched_mw
                    cur_ask["mw"] -= matched_mw

                if cur_bid["mw"] <= 0.01:
                    b_idx += 1
                if cur_ask["mw"] <= 0.01:
                    s_idx += 1
            else:
                # No more profitable trades can be matched
                break

        # Uniform Clearing Price = Midpoint of the marginal cleared bid and ask
        mcp = (last_cleared_bid + last_cleared_ask) / 2.0 if total_mw > 0 else (asks[0]["price_usd_mwh"] + 5.0)
        
        # Calculate economic surpluses
        cons_surplus = sum((t["bid_price"] - mcp) * t["mw"] for t in cleared_trades if t["bid_price"] > mcp)
        prod_surplus = sum((mcp - t["ask_price"]) * t["mw"] for t in cleared_trades if mcp > t["ask_price"])

        return cleared_trades, mcp, total_mw, cons_surplus, prod_surplus
