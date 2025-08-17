"""
Agent Marketplace - Sistema de Subastas Internas
Marketplace darwiniano donde los agentes compiten por tareas
"""
import asyncio
import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import uuid4
import math
import redis

from .agent_dna import genetic_engine, AgentDNA, SpecializationType
from .colony_manager import colony_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

class TaskCategory(Enum):
    """Categorías de tareas en el marketplace"""
    FISCAL_SAT = "fiscal_sat"
    SALES_AUTOMATION = "sales_automation"
    CUSTOMER_SUPPORT = "customer_support"
    DATA_PROCESSING = "data_processing"
    WEB_SCRAPING = "web_scraping"
    API_INTEGRATION = "api_integration"
    BUSINESS_INTELLIGENCE = "business_intelligence"
    MARKETING = "marketing"
    ACCOUNTING = "accounting"
    GENERAL = "general"

class TaskPriority(Enum):
    """Prioridad de las tareas"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

class BidStatus(Enum):
    """Estado de las pujas"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class Task:
    """Tarea en el marketplace"""
    task_id: str
    user_id: str
    title: str
    description: str
    category: TaskCategory
    priority: TaskPriority
    estimated_complexity: float  # 0.0 - 1.0
    max_budget: float  # Budget máximo en USD
    deadline: Optional[float] = None  # Timestamp
    required_skills: List[str] = None
    context_data: Dict[str, Any] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.required_skills is None:
            self.required_skills = []
        if self.context_data is None:
            self.context_data = {}
        if self.created_at is None:
            self.created_at = time.time()

@dataclass
class AgentBid:
    """Puja de un agente para una tarea"""
    bid_id: str
    agent_id: str
    task_id: str
    confidence_score: float  # 0.0 - 1.0 (qué tan seguro está de poder hacerla)
    estimated_time: float  # Tiempo estimado en segundos
    estimated_cost: float  # Costo estimado en USD
    bid_amount: float  # Cuánto cobra por la tarea
    specialization_match: float  # Qué tan bien encaja con su especialización
    performance_history: Dict[str, float] = None  # Métricas históricas
    reasoning: str = ""  # Por qué cree que puede hacer la tarea
    created_at: float = None
    status: BidStatus = BidStatus.PENDING
    
    def __post_init__(self):
        if self.performance_history is None:
            self.performance_history = {}
        if self.created_at is None:
            self.created_at = time.time()
    
    def calculate_bid_score(self) -> float:
        """
        Calcula score total de la puja para ranking
        Más alto = mejor puja
        """
        # Weighted scoring
        score = (
            self.confidence_score * 0.4 +  # 40% confianza
            self.specialization_match * 0.3 +  # 30% match especialización
            (1.0 - min(self.estimated_time / 3600, 1.0)) * 0.2 +  # 20% velocidad (max 1 hora)
            (1.0 - min(self.bid_amount / 100, 1.0)) * 0.1  # 10% precio (max $100)
        )
        
        # Bonus por historial de performance
        if self.performance_history.get("avg_success_rate", 0) > 0.8:
            score *= 1.2  # 20% bonus
        
        return min(1.0, score)

@dataclass
class TaskAssignment:
    """Asignación de tarea a agente ganador"""
    assignment_id: str
    task_id: str
    winning_agent_id: str
    winning_bid_id: str
    assigned_at: float
    expected_completion: float
    actual_completion: Optional[float] = None
    task_result: Optional[Dict[str, Any]] = None
    performance_rating: Optional[float] = None  # 0.0 - 1.0
    status: str = "assigned"  # assigned, in_progress, completed, failed
    
class AgentMarketplace:
    """
    Sistema de marketplace interno donde agentes compiten por tareas
    
    Funcionalidades:
    - Sistema de subastas por tareas
    - Scoring automático de pujas
    - Asignación basada en competencia
    - Tracking de performance por agente
    - Feedback loop para mejorar scoring
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis = redis.from_url(self.redis_url) if self.redis_url else None
        self.genetic_engine = genetic_engine
        self.colony_manager = colony_manager
        
        # Active auctions and assignments
        self.active_tasks: Dict[str, Task] = {}
        self.active_bids: Dict[str, List[AgentBid]] = {}  # task_id -> list of bids
        self.assignments: Dict[str, TaskAssignment] = {}
        
        # Auction settings
        self.auction_duration = 30  # 30 seconds for bidding
        self.min_bidders = 2  # Minimum bidders for valid auction
        self.max_bidders = 10  # Maximum bidders per task
        
        # Performance tracking
        self.agent_performance_history: Dict[str, Dict[str, Any]] = {}
        
    async def submit_task(self, task: Task) -> str:
        """
        Submite una nueva tarea al marketplace
        Inicia proceso de subasta automáticamente
        """
        task_id = task.task_id
        self.active_tasks[task_id] = task
        self.active_bids[task_id] = []
        
        # Log task submission
        await self._log_marketplace_event("task_submitted", {
            "task_id": task_id,
            "category": task.category.value,
            "priority": task.priority.value,
            "max_budget": task.max_budget
        })
        
        # Start auction process
        asyncio.create_task(self._run_auction(task_id))
        
        logger.info(f"Task {task_id} submitted to marketplace ({task.category.value}, ${task.max_budget})")
        return task_id
    
    async def _run_auction(self, task_id: str):
        """
        Ejecuta el proceso completo de subasta para una tarea
        """
        if task_id not in self.active_tasks:
            return
        
        task = self.active_tasks[task_id]
        
        try:
            # 1. Invitar agentes elegibles a pujar
            eligible_agents = await self._find_eligible_agents(task)
            
            if not eligible_agents:
                await self._handle_no_eligible_agents(task_id)
                return
            
            # 2. Notificar agentes y esperar pujas
            await self._invite_agents_to_bid(task_id, eligible_agents)
            
            # 3. Esperar período de puja
            await asyncio.sleep(self.auction_duration)
            
            # 4. Evaluar pujas y seleccionar ganador
            winning_bid = await self._evaluate_bids(task_id)
            
            if winning_bid:
                # 5. Asignar tarea al ganador
                assignment = await self._assign_task(task_id, winning_bid)
                await self._notify_auction_results(task_id, winning_bid, assignment)
            else:
                await self._handle_no_valid_bids(task_id)
                
        except Exception as e:
            logger.error(f"Error in auction for task {task_id}: {e}")
            await self._handle_auction_error(task_id, str(e))
    
    async def submit_bid(self, agent_id: str, task_id: str, bid_data: Dict[str, Any]) -> bool:
        """
        Permite a un agente enviar una puja para una tarea
        """
        if task_id not in self.active_tasks:
            return False
        
        if task_id not in self.active_bids:
            return False
        
        # Verificar que el agente sea elegible
        if not await self._is_agent_eligible(agent_id, task_id):
            return False
        
        # Verificar que no haya pujado ya
        existing_bid = next((bid for bid in self.active_bids[task_id] if bid.agent_id == agent_id), None)
        if existing_bid:
            return False  # Ya pujó
        
        # Calcular métricas automáticas
        agent_dna = self.genetic_engine.agents_registry.get(agent_id)
        if not agent_dna:
            return False
        
        task = self.active_tasks[task_id]
        
        # Auto-calculate bid parameters if not provided
        confidence_score = bid_data.get("confidence_score", 
                                       await self._calculate_confidence(agent_dna, task))
        estimated_time = bid_data.get("estimated_time",
                                    await self._estimate_execution_time(agent_dna, task))
        estimated_cost = bid_data.get("estimated_cost",
                                    await self._estimate_cost(agent_dna, task))
        bid_amount = bid_data.get("bid_amount", estimated_cost * 1.2)  # 20% markup
        
        specialization_match = await self._calculate_specialization_match(agent_dna, task)
        performance_history = self.agent_performance_history.get(agent_id, {})
        
        # Crear puja
        bid = AgentBid(
            bid_id=f"bid_{uuid4().hex[:8]}",
            agent_id=agent_id,
            task_id=task_id,
            confidence_score=confidence_score,
            estimated_time=estimated_time,
            estimated_cost=estimated_cost,
            bid_amount=bid_amount,
            specialization_match=specialization_match,
            performance_history=performance_history,
            reasoning=bid_data.get("reasoning", f"I can handle this {task.category.value} task with {confidence_score:.0%} confidence")
        )
        
        self.active_bids[task_id].append(bid)
        
        await self._log_marketplace_event("bid_submitted", {
            "bid_id": bid.bid_id,
            "agent_id": agent_id,
            "task_id": task_id,
            "confidence": confidence_score,
            "bid_amount": bid_amount,
            "bid_score": bid.calculate_bid_score()
        })
        
        logger.info(f"Agent {agent_id} bid on task {task_id} (confidence: {confidence_score:.2f}, amount: ${bid_amount:.2f})")
        return True
    
    async def complete_task(self, assignment_id: str, result: Dict[str, Any], performance_rating: float = None) -> bool:
        """
        Marca una tarea como completada y actualiza métricas
        """
        if assignment_id not in self.assignments:
            return False
        
        assignment = self.assignments[assignment_id]
        assignment.actual_completion = time.time()
        assignment.task_result = result
        assignment.performance_rating = performance_rating
        assignment.status = "completed" if result.get("status") == "success" else "failed"
        
        # Update agent performance history
        await self._update_agent_performance(assignment.winning_agent_id, assignment, result)
        
        # Update genetic engine performance
        task_result = {
            "status": result.get("status", "success"),
            "response_time": assignment.actual_completion - assignment.assigned_at,
            "accuracy_score": performance_rating or (1.0 if result.get("status") == "success" else 0.0),
            "user_rating": performance_rating or 0.8,
            "cost": assignment.winning_bid_id  # Will need to get actual bid amount
        }
        
        self.genetic_engine.update_performance(assignment.winning_agent_id, task_result)
        
        await self._log_marketplace_event("task_completed", {
            "assignment_id": assignment_id,
            "agent_id": assignment.winning_agent_id,
            "task_id": assignment.task_id,
            "success": assignment.status == "completed",
            "performance_rating": performance_rating,
            "execution_time": assignment.actual_completion - assignment.assigned_at
        })
        
        logger.info(f"Task {assignment.task_id} completed by agent {assignment.winning_agent_id} "
                   f"(status: {assignment.status}, rating: {performance_rating})")
        
        return True
    
    async def get_marketplace_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del marketplace
        """
        active_tasks_count = len(self.active_tasks)
        total_bids = sum(len(bids) for bids in self.active_bids.values())
        active_assignments = len([a for a in self.assignments.values() if a.status in ["assigned", "in_progress"]])
        completed_assignments = len([a for a in self.assignments.values() if a.status == "completed"])
        
        # Top performers
        performance_scores = {}
        for agent_id, history in self.agent_performance_history.items():
            if history.get("total_tasks", 0) > 0:
                performance_scores[agent_id] = history.get("avg_performance", 0.0)
        
        top_performers = sorted(performance_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Category distribution
        category_stats = {}
        for task in self.active_tasks.values():
            cat = task.category.value
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        return {
            "active_tasks": active_tasks_count,
            "total_bids": total_bids,
            "active_assignments": active_assignments,
            "completed_assignments": completed_assignments,
            "avg_bids_per_task": total_bids / max(active_tasks_count, 1),
            "top_performers": top_performers,
            "category_distribution": category_stats,
            "marketplace_activity": {
                "last_24h_tasks": await self._count_recent_tasks(86400),
                "last_24h_assignments": await self._count_recent_assignments(86400),
                "avg_auction_duration": self.auction_duration
            }
        }
    
    async def get_agent_marketplace_profile(self, agent_id: str) -> Dict[str, Any]:
        """
        Obtiene perfil de un agente en el marketplace
        """
        agent_dna = self.genetic_engine.agents_registry.get(agent_id)
        if not agent_dna:
            return {"error": "Agent not found"}
        
        performance_history = self.agent_performance_history.get(agent_id, {})
        
        # Recent bids and assignments
        recent_bids = []
        recent_assignments = []
        
        for task_id, bids in self.active_bids.items():
            agent_bid = next((bid for bid in bids if bid.agent_id == agent_id), None)
            if agent_bid:
                recent_bids.append({
                    "task_id": task_id,
                    "bid_score": agent_bid.calculate_bid_score(),
                    "confidence": agent_bid.confidence_score,
                    "bid_amount": agent_bid.bid_amount,
                    "status": agent_bid.status.value
                })
        
        for assignment in self.assignments.values():
            if assignment.winning_agent_id == agent_id:
                recent_assignments.append({
                    "task_id": assignment.task_id,
                    "assigned_at": assignment.assigned_at,
                    "status": assignment.status,
                    "performance_rating": assignment.performance_rating
                })
        
        return {
            "agent_id": agent_id,
            "specialization": agent_dna.traits.specialization.value,
            "fitness_score": agent_dna.performance.fitness_score,
            "generation": agent_dna.generation,
            "marketplace_performance": performance_history,
            "recent_bids": recent_bids[-10:],  # Last 10 bids
            "recent_assignments": recent_assignments[-10:],  # Last 10 assignments
            "bidding_preferences": {
                "preferred_categories": await self._get_preferred_categories(agent_id),
                "avg_confidence": performance_history.get("avg_confidence", 0.0),
                "avg_bid_amount": performance_history.get("avg_bid_amount", 0.0)
            }
        }
    
    async def _find_eligible_agents(self, task: Task) -> List[str]:
        """
        Encuentra agentes elegibles para pujar en una tarea
        """
        eligible_agents = []
        
        for agent_id, agent_dna in self.genetic_engine.agents_registry.items():
            if not agent_dna.is_active:
                continue
            
            # Check if agent can handle the category
            specialization_match = await self._calculate_specialization_match(agent_dna, task)
            if specialization_match < 0.2:  # Minimum 20% match
                continue
            
            # Check if agent is not overloaded
            current_assignments = len([a for a in self.assignments.values() 
                                     if a.winning_agent_id == agent_id and a.status in ["assigned", "in_progress"]])
            
            max_concurrent = max(1, int(agent_dna.traits.cooperation_level * 5))  # 1-5 based on cooperation
            if current_assignments >= max_concurrent:
                continue
            
            # Check performance history (don't invite consistently failing agents)
            agent_performance = self.agent_performance_history.get(agent_id, {})
            if agent_performance.get("total_tasks", 0) > 5 and agent_performance.get("avg_performance", 1.0) < 0.3:
                continue
            
            eligible_agents.append(agent_id)
        
        # Limit to max bidders, prioritize by fitness
        if len(eligible_agents) > self.max_bidders:
            agent_fitness = [(agent_id, self.genetic_engine.agents_registry[agent_id].performance.fitness_score) 
                           for agent_id in eligible_agents]
            agent_fitness.sort(key=lambda x: x[1], reverse=True)
            eligible_agents = [agent_id for agent_id, _ in agent_fitness[:self.max_bidders]]
        
        return eligible_agents
    
    async def _invite_agents_to_bid(self, task_id: str, eligible_agents: List[str]):
        """
        Invita a agentes elegibles a pujar (simula notificación)
        """
        task = self.active_tasks[task_id]
        
        for agent_id in eligible_agents:
            # Auto-generate bid (simulates agent decision-making)
            await self._auto_generate_bid(agent_id, task_id)
    
    async def _auto_generate_bid(self, agent_id: str, task_id: str):
        """
        Auto-genera una puja para un agente (simula proceso de decisión del agente)
        """
        agent_dna = self.genetic_engine.agents_registry.get(agent_id)
        if not agent_dna:
            return
        
        task = self.active_tasks[task_id]
        
        # Simulate agent thinking time based on traits
        thinking_time = (1.0 - agent_dna.traits.speed_vs_accuracy) * 20 + 2  # 2-22 seconds
        await asyncio.sleep(thinking_time)
        
        # Calculate bid parameters
        confidence = await self._calculate_confidence(agent_dna, task)
        
        # Agent may choose not to bid if confidence is too low
        if confidence < 0.3 and agent_dna.traits.risk_tolerance < 0.5:
            return  # Too risky, don't bid
        
        # Submit auto-generated bid
        bid_data = {
            "confidence_score": confidence,
            "reasoning": f"Auto-generated bid based on {agent_dna.traits.specialization.value} specialization"
        }
        
        await self.submit_bid(agent_id, task_id, bid_data)
    
    async def _evaluate_bids(self, task_id: str) -> Optional[AgentBid]:
        """
        Evalúa todas las pujas y selecciona al ganador
        """
        if task_id not in self.active_bids:
            return None
        
        bids = self.active_bids[task_id]
        
        if len(bids) < self.min_bidders:
            return None  # Not enough bidders
        
        # Calculate bid scores and rank
        scored_bids = []
        for bid in bids:
            score = bid.calculate_bid_score()
            scored_bids.append((bid, score))
        
        # Sort by score (highest first)
        scored_bids.sort(key=lambda x: x[1], reverse=True)
        
        # Winner is highest scoring bid
        winning_bid = scored_bids[0][0]
        winning_bid.status = BidStatus.ACCEPTED
        
        # Mark other bids as rejected
        for bid, _ in scored_bids[1:]:
            bid.status = BidStatus.REJECTED
        
        return winning_bid
    
    async def _assign_task(self, task_id: str, winning_bid: AgentBid) -> TaskAssignment:
        """
        Asigna la tarea al agente ganador
        """
        assignment_id = f"assign_{uuid4().hex[:8]}"
        
        assignment = TaskAssignment(
            assignment_id=assignment_id,
            task_id=task_id,
            winning_agent_id=winning_bid.agent_id,
            winning_bid_id=winning_bid.bid_id,
            assigned_at=time.time(),
            expected_completion=time.time() + winning_bid.estimated_time
        )
        
        self.assignments[assignment_id] = assignment
        
        # Remove task from active tasks
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        
        return assignment
    
    async def _calculate_confidence(self, agent_dna: AgentDNA, task: Task) -> float:
        """
        Calcula confianza del agente para realizar la tarea
        """
        # Base confidence from domain expertise
        base_confidence = agent_dna.traits.domain_expertise
        
        # Adjust based on specialization match
        specialization_match = await self._calculate_specialization_match(agent_dna, task)
        confidence = base_confidence * specialization_match
        
        # Adjust based on task complexity vs agent experience
        complexity_factor = 1.0 - (task.estimated_complexity * 0.5)
        confidence *= complexity_factor
        
        # Adjust based on risk tolerance and task priority
        if task.priority.value >= 4:  # Urgent/Critical tasks
            if agent_dna.traits.risk_tolerance < 0.5:
                confidence *= 0.8  # Conservative agents less confident in high-pressure tasks
        
        # Performance history adjustment
        if agent_dna.performance.total_tasks > 5:
            performance_modifier = agent_dna.performance.fitness_score
            confidence = (confidence * 0.7) + (performance_modifier * 0.3)
        
        return max(0.1, min(1.0, confidence))
    
    async def _calculate_specialization_match(self, agent_dna: AgentDNA, task: Task) -> float:
        """
        Calcula qué tan bien encaja la especialización del agente con la tarea
        """
        # Direct specialization mapping
        specialization_mapping = {
            SpecializationType.SAT_FISCAL: [TaskCategory.FISCAL_SAT, TaskCategory.ACCOUNTING],
            SpecializationType.SALES_AUTOMATION: [TaskCategory.SALES_AUTOMATION, TaskCategory.MARKETING],
            SpecializationType.CUSTOMER_SUPPORT: [TaskCategory.CUSTOMER_SUPPORT],
            SpecializationType.DATA_PROCESSING: [TaskCategory.DATA_PROCESSING, TaskCategory.BUSINESS_INTELLIGENCE],
            SpecializationType.WEB_SCRAPING: [TaskCategory.WEB_SCRAPING, TaskCategory.DATA_PROCESSING],
            SpecializationType.API_INTEGRATION: [TaskCategory.API_INTEGRATION, TaskCategory.DATA_PROCESSING],
            SpecializationType.BUSINESS_INTELLIGENCE: [TaskCategory.BUSINESS_INTELLIGENCE, TaskCategory.DATA_PROCESSING],
            SpecializationType.MARKETING_AUTOMATION: [TaskCategory.MARKETING, TaskCategory.SALES_AUTOMATION],
            SpecializationType.ACCOUNTING_FINANCE: [TaskCategory.ACCOUNTING, TaskCategory.FISCAL_SAT],
            SpecializationType.GENERALIST: list(TaskCategory)  # Can handle any category but not as well
        }
        
        agent_specialization = agent_dna.traits.specialization
        compatible_categories = specialization_mapping.get(agent_specialization, [])
        
        if task.category in compatible_categories:
            if agent_specialization == SpecializationType.GENERALIST:
                return 0.6  # Generalists are okay at everything
            else:
                primary_match = compatible_categories[0] == task.category
                return 1.0 if primary_match else 0.8  # Perfect or good match
        else:
            # Cross-domain penalties
            return 0.3 if agent_specialization == SpecializationType.GENERALIST else 0.1
    
    async def _estimate_execution_time(self, agent_dna: AgentDNA, task: Task) -> float:
        """
        Estima tiempo de ejecución basado en traits del agente
        """
        # Base time based on task complexity
        base_time = 60 + (task.estimated_complexity * 300)  # 1-6 minutes base
        
        # Adjust based on speed vs accuracy preference
        speed_factor = 2.0 - agent_dna.traits.speed_vs_accuracy  # 1.0 to 2.0
        estimated_time = base_time * speed_factor
        
        # Adjust based on domain expertise
        expertise_factor = 2.0 - agent_dna.traits.domain_expertise  # 1.0 to 2.0
        estimated_time *= expertise_factor
        
        # Adjust based on specialization match
        specialization_match = await self._calculate_specialization_match(agent_dna, task)
        estimated_time *= (2.0 - specialization_match)  # Better match = faster execution
        
        return max(30, estimated_time)  # Minimum 30 seconds
    
    async def _estimate_cost(self, agent_dna: AgentDNA, task: Task) -> float:
        """
        Estima costo basado en complejidad y expertise del agente
        """
        # Base cost calculation
        base_cost = 1.0 + (task.estimated_complexity * 5.0)  # $1-6 base
        
        # Premium for higher expertise
        expertise_premium = agent_dna.traits.domain_expertise * 2.0
        cost = base_cost + expertise_premium
        
        # Specialization premium
        specialization_match = await self._calculate_specialization_match(agent_dna, task)
        if specialization_match > 0.8:
            cost *= 1.5  # 50% premium for specialists
        
        # Performance history premium
        if agent_dna.performance.fitness_score > 0.8:
            cost *= 1.2  # 20% premium for high performers
        
        return min(cost, task.max_budget * 0.8)  # Don't exceed 80% of budget
    
    async def _update_agent_performance(self, agent_id: str, assignment: TaskAssignment, result: Dict[str, Any]):
        """
        Actualiza historial de performance del agente
        """
        if agent_id not in self.agent_performance_history:
            self.agent_performance_history[agent_id] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "avg_performance": 0.0,
                "avg_confidence": 0.0,
                "avg_bid_amount": 0.0,
                "total_earnings": 0.0
            }
        
        history = self.agent_performance_history[agent_id]
        
        # Update counters
        history["total_tasks"] += 1
        if assignment.status == "completed":
            history["successful_tasks"] += 1
        
        # Update averages
        n = history["total_tasks"]
        rating = assignment.performance_rating or (1.0 if assignment.status == "completed" else 0.0)
        
        history["avg_performance"] = ((history["avg_performance"] * (n-1)) + rating) / n
        
        # Get bid info (would need to look up actual bid)
        # For now, using placeholder values
        history["avg_confidence"] = ((history["avg_confidence"] * (n-1)) + 0.7) / n
        history["avg_bid_amount"] = ((history["avg_bid_amount"] * (n-1)) + 5.0) / n
        history["total_earnings"] += 5.0  # Placeholder
    
    async def _is_agent_eligible(self, agent_id: str, task_id: str) -> bool:
        """
        Verifica si un agente es elegible para pujar
        """
        agent_dna = self.genetic_engine.agents_registry.get(agent_id)
        if not agent_dna or not agent_dna.is_active:
            return False
        
        task = self.active_tasks.get(task_id)
        if not task:
            return False
        
        # Check specialization compatibility
        specialization_match = await self._calculate_specialization_match(agent_dna, task)
        return specialization_match >= 0.2
    
    async def _log_marketplace_event(self, event_type: str, data: Dict[str, Any]):
        """
        Registra evento del marketplace
        """
        if not self.redis:
            return
        
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "data": data
        }
        
        try:
            events_key = "marketplace_events"
            self.redis.lpush(events_key, json.dumps(event, default=str))
            self.redis.ltrim(events_key, 0, 999)  # Keep last 1000 events
            self.redis.expire(events_key, 604800)  # 7 days
        except Exception as e:
            logger.error(f"Failed to log marketplace event: {e}")
    
    async def _handle_no_eligible_agents(self, task_id: str):
        """Maneja caso donde no hay agentes elegibles"""
        logger.warning(f"No eligible agents found for task {task_id}")
        await self._log_marketplace_event("no_eligible_agents", {"task_id": task_id})
    
    async def _handle_no_valid_bids(self, task_id: str):
        """Maneja caso donde no hay pujas válidas"""
        logger.warning(f"No valid bids received for task {task_id}")
        await self._log_marketplace_event("no_valid_bids", {"task_id": task_id})
    
    async def _handle_auction_error(self, task_id: str, error: str):
        """Maneja errores en subasta"""
        logger.error(f"Auction error for task {task_id}: {error}")
        await self._log_marketplace_event("auction_error", {"task_id": task_id, "error": error})
    
    async def _notify_auction_results(self, task_id: str, winning_bid: AgentBid, assignment: TaskAssignment):
        """Notifica resultados de subasta"""
        await self._log_marketplace_event("auction_completed", {
            "task_id": task_id,
            "winning_agent": winning_bid.agent_id,
            "winning_bid_score": winning_bid.calculate_bid_score(),
            "assignment_id": assignment.assignment_id
        })
    
    async def _count_recent_tasks(self, seconds: int) -> int:
        """Cuenta tareas recientes"""
        cutoff = time.time() - seconds
        return len([task for task in self.active_tasks.values() if task.created_at > cutoff])
    
    async def _count_recent_assignments(self, seconds: int) -> int:
        """Cuenta asignaciones recientes"""
        cutoff = time.time() - seconds
        return len([assignment for assignment in self.assignments.values() if assignment.assigned_at > cutoff])
    
    async def _get_preferred_categories(self, agent_id: str) -> List[str]:
        """Obtiene categorías preferidas basadas en historial"""
        # TODO: Implement based on bid history
        agent_dna = self.genetic_engine.agents_registry.get(agent_id)
        if agent_dna:
            return [agent_dna.traits.specialization.value]
        return []

# Global marketplace instance
agent_marketplace = AgentMarketplace()