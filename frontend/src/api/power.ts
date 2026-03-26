import api from './client';
import { PowerHistoryResponse, RecentPowerResponse } from '../types/power';

export async function getCurrentPower() {
  const response = await api.get('/power/current');
  return response.data;
}

export async function getTotalKwh() {
  const response = await api.get('/power/total-kwh');
  return response.data;
}

export async function getPowerHistory(startDate: Date, endDate: Date): Promise<PowerHistoryResponse> {
  const response = await api.get('/power/history', {
    params: {
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
    },
  });
  return response.data;
}

export async function getRecentReadings(hours: number = 24): Promise<RecentPowerResponse> {
  const response = await api.get('/power/recent', {
    params: { hours },
  });
  return response.data;
}
