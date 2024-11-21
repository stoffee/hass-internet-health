import logging
import asyncio
import aiohttp
import socket
from datetime import datetime
from typing import List, Dict
import dns.resolver

_LOGGER = logging.getLogger(__name__)

class InternetHealthChecker:
    def __init__(self, hass):
        self.hass = hass
        self.last_check_time = None
        self.failed_checks = []
        self.confidence_score = 0
        self.tcp_ports = [80, 443]
        self.tcp_targets = [
            ('google.com', 'Google'),
            ('amazon.com', 'Amazon'),
            ('cloudflare.com', 'Cloudflare'),
            ('github.com', 'GitHub'),
            ('microsoft.com', 'Microsoft')
        ]

    async def check_dns_multi(self) -> Dict:
        """Test DNS resolution using multiple nameservers."""
        nameservers = [
            ('8.8.8.8', 'Google'),
            ('1.1.1.1', 'Cloudflare'),
            ('9.9.9.9', 'Quad9'),
            ('208.67.222.222', 'OpenDNS')
        ]
        results = {}
        success = 0

        for server, name in nameservers:
            try:
                _LOGGER.warning(f"Testing DNS using {name}...")
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [server]
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: resolver.resolve('google.com', 'A'))
                results[name.lower()] = True
                success += 1
                _LOGGER.warning(f"✓ DNS using {name} successful!")
            except Exception as e:
                self.failed_checks.append(f"DNS ({name}) check failed: {str(e)}")
                results[name.lower()] = False

        return {
            'success': success >= 2,
            'details': results,
            'success_count': success,
            'total_count': len(nameservers)
        }

    async def check_tcp_ports(self) -> Dict:
        """Test TCP connectivity to major sites."""
        results = {}
        success_count = 0
        total_checks = len(self.tcp_targets) * len(self.tcp_ports)

        for host, name in self.tcp_targets:
            host_results = {}
            for port in self.tcp_ports:
                try:
                    _LOGGER.warning(f"Testing TCP {port} to {name}...")
                    reader, writer = await asyncio.open_connection(host, port)
                    writer.close()
                    await writer.wait_closed()
                    host_results[f'port_{port}'] = True
                    _LOGGER.warning(f"✓ TCP {port} to {name} successful!")
                    success_count += 1
                except Exception as e:
                    self.failed_checks.append(f"TCP {port} to {name} failed: {str(e)}")
                    host_results[f'port_{port}'] = False
            results[name.lower()] = host_results

        return {
            'success': success_count >= (total_checks // 2),
            'details': results,
            'success_count': success_count,
            'total_count': total_checks
        }

    async def check_http_connectivity(self) -> Dict:
        """Test HTTP connectivity to major sites."""
        urls = [
            'http://www.google.com',
            'http://www.cloudflare.com',
            'http://www.apple.com'
        ]
        results = {}
        success_count = 0

        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    _LOGGER.warning(f"Testing HTTP to {url}...")
                    async with session.get(url, timeout=5) as response:
                        success = response.status == 200
                        results[url] = success
                        if success:
                            success_count += 1
                            _LOGGER.warning(f"✓ HTTP to {url} successful!")
                except Exception as e:
                    self.failed_checks.append(f"HTTP check to {url} failed: {str(e)}")
                    results[url] = False

        return {
            'success': success_count >= (len(urls) // 2),
            'details': results,
            'success_count': success_count,
            'total_count': len(urls)
        }

    def calculate_confidence(self, results: Dict) -> float:
        """Calculate confidence level in internet status."""
        weights = {
            'tcp': 0.45,
            'http': 0.35,
            'dns': 0.20
        }

        confidence = 0
        _LOGGER.warning("Calculating confidence scores:")

        for test, weight in weights.items():
            if test in results and results[test]['success']:
                success_rate = results[test].get('success_count', 0) / results[test].get('total_count', 1)
                test_confidence = weight * success_rate
                confidence += test_confidence
                _LOGGER.warning(f"{test}: {success_rate*100}% success rate = {test_confidence*100}% confidence contribution")

        final_confidence = round(confidence * 100, 1)
        _LOGGER.warning(f"Total confidence: {final_confidence}%")
        return final_confidence

    async def update_check_history(self, passed_checks: int):
        """Update the rolling history of health checks."""
        try:
            for i in range(1, 3):
                old_value = float(self.hass.states.get(f'input_number.internet_health_check_{i}').state)
                await self.hass.services.async_call(
                    'input_number', 'set_value',
                    {'entity_id': f'input_number.internet_health_check_{i+1}', 'value': old_value}
                )

            await self.hass.services.async_call(
                'input_number', 'set_value',
                {'entity_id': 'input_number.internet_health_check_1', 'value': passed_checks}
            )

            _LOGGER.info(f"Updated health check history: {passed_checks}")
        except Exception as e:
            _LOGGER.error(f"Failed to update check history: {str(e)}")

    async def check_all(self) -> Dict:
        """Run all internet health checks and return results."""
        _LOGGER.warning("🌊 Starting enhanced internet health checks")
        self.failed_checks = []
        self.last_check_time = datetime.now()

        try:
            tcp_result, http_result, dns_result = await asyncio.gather(
                self.check_tcp_ports(),
                self.check_http_connectivity(),
                self.check_dns_multi()
            )

            results = {
                'tcp': tcp_result,
                'http': http_result,
                'dns': dns_result
            }

            confidence = self.calculate_confidence(results)
            passed_checks = sum(1 for r in results.values() if r['success'])

            await self.update_check_history(passed_checks)

            status = tcp_result['success'] and http_result['success'] and confidence >= 60

            return {
                'status': status,
                'timestamp': self.last_check_time,
                'confidence': confidence,
                'checks': results,
                'failed_reasons': self.failed_checks,
                'passed_checks': passed_checks,
                'total_checks': len(results)
            }

        except Exception as e:
            _LOGGER.error(f"Auwe! Big crash in health check: {str(e)}")
            await self.update_check_history(0)
            return {
                'status': False,
                'timestamp': self.last_check_time,
                'confidence': 0,
                'checks': {},
                'failed_reasons': [f"System error: {str(e)}"],
                'passed_checks': 0,
                'total_checks': 3
            }

async def async_setup(hass, config):
    """Set up the Internet Health Check component."""
    _LOGGER.info("Setting up Enhanced Internet Health Check component")

    try:
        checker = InternetHealthChecker(hass)

        async def async_check_internet(call):
            """Handle the service call."""
            try:
                _LOGGER.info("Internet health check service called")
                result = await checker.check_all()

                _LOGGER.warning(f"Setting sensor state: {'online' if result['status'] else 'offline'}")
                hass.states.async_set(
                    'sensor.internet_health',
                    'online' if result['status'] else 'offline',
                    attributes=result
                )
            except Exception as e:
                _LOGGER.error(f"Auwe! Check wen crash: {str(e)}")
                hass.states.async_set(
                    'sensor.internet_health',
                    'offline',
                    attributes={
                        'status': False,
                        'confidence': 0,
                        'passed_checks': 0,
                        'error': str(e)
                    }
                )

        # Register the service
        hass.services.async_register('internet_health', 'check', async_check_internet)
        _LOGGER.info("Enhanced Internet Health Check component setup completed")

        return True

    except Exception as e:
        _LOGGER.error(f"Failed to set up Internet Health Check component: {str(e)}")
        return False
