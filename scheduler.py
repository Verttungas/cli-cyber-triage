import os
import sys
import signal
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from incident_processor import IncidentProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('./logs/scheduler.log')
    ]
)
logger = logging.getLogger(__name__)

SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))
HOURS_BACK = int(os.getenv("HOURS_BACK", "24"))
MAX_ANALYSIS_PER_CYCLE = int(os.getenv("MAX_ANALYSIS_PER_CYCLE", "10"))
CLEANUP_DAYS = int(os.getenv("CLEANUP_DAYS", "30"))


class CyberTriageScheduler:
    
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.processor = None
        self.is_running = False
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        logger.info(f"Señal {signum} recibida. Deteniendo scheduler...")
        self.stop()
    
    def _init_processor(self):
        if self.processor is None:
            self.processor = IncidentProcessor()
        return self.processor
    
    def job_process_incidents(self):
        logger.info("=" * 50)
        logger.info("JOB: Iniciando ciclo de procesamiento")
        logger.info("=" * 50)
        
        try:
            processor = self._init_processor()
            result = processor.run_full_cycle(
                hours_back=HOURS_BACK,
                max_analysis=MAX_ANALYSIS_PER_CYCLE
            )
            logger.info(f"JOB completado: {result}")
        except Exception as e:
            logger.error(f"JOB error: {e}", exc_info=True)
    
    def job_cleanup_old_data(self):
        logger.info("JOB: Limpieza de datos antiguos")
        
        try:
            processor = self._init_processor()
            deleted = processor.db.clear_old_data(days=CLEANUP_DAYS)
            logger.info(f"Limpieza completada: {deleted[0]} incidentes, {deleted[1]} análisis, {deleted[2]} feedback")
        except Exception as e:
            logger.error(f"Error en limpieza: {e}")
    
    def job_health_check(self):
        try:
            processor = self._init_processor()
            stats = processor.db.get_database_stats()
            pending = len(processor.db.get_pending_incidents(limit=100))
            
            logger.info(f"HEALTH: OK | Pendientes: {pending} | Total análisis: {stats.get('total_analyses', 0)}")
        except Exception as e:
            logger.error(f"HEALTH: FAIL | {e}")
    
    def start(self):
        logger.info("=" * 60)
        logger.info("CYBER-TRIAGE SCHEDULER INICIANDO")
        logger.info(f"  Intervalo de escaneo: {SCAN_INTERVAL_MINUTES} minutos")
        logger.info(f"  Horas hacia atrás: {HOURS_BACK}")
        logger.info(f"  Max análisis por ciclo: {MAX_ANALYSIS_PER_CYCLE}")
        logger.info("=" * 60)
        
        os.makedirs('./logs', exist_ok=True)
        
        self.scheduler.add_job(
            self.job_process_incidents,
            trigger=IntervalTrigger(minutes=SCAN_INTERVAL_MINUTES),
            id='process_incidents',
            name='Procesar incidentes HIGH/CRITICAL',
            replace_existing=True,
            max_instances=1
        )
        
        self.scheduler.add_job(
            self.job_cleanup_old_data,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_old_data',
            name='Limpieza nocturna de datos antiguos',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self.job_health_check,
            trigger=IntervalTrigger(minutes=5),
            id='health_check',
            name='Health check',
            replace_existing=True
        )
        
        logger.info("Ejecutando ciclo inicial...")
        self.job_process_incidents()
        
        logger.info("Scheduler iniciado. Esperando próximos ciclos...")
        self.is_running = True
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.stop()
    
    def stop(self):
        if self.is_running:
            logger.info("Deteniendo scheduler...")
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Scheduler detenido correctamente")


def run_once():
    logger.info("Ejecutando ciclo único (sin scheduler)")
    processor = IncidentProcessor()
    result = processor.run_full_cycle(
        hours_back=HOURS_BACK,
        max_analysis=MAX_ANALYSIS_PER_CYCLE
    )
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Cyber-Triage Scheduler')
    parser.add_argument('--once', action='store_true', help='Ejecutar un solo ciclo y salir')
    parser.add_argument('--daemon', action='store_true', help='Ejecutar como daemon continuo')
    args = parser.parse_args()
    
    if args.once:
        result = run_once()
        print(f"Resultado: {result}")
        sys.exit(0)
    else:
        scheduler = CyberTriageScheduler()
        scheduler.start()


if __name__ == "__main__":
    main()