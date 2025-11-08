import { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  TrendingUp,
  AttachMoney,
  Speed,
  Person,
  SmartToy,
  Memory,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import adminApi from '../api/admin';
import MainLayout from '../layouts/MainLayout';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#ff7300'];

export default function Analytics() {
  const [timeRange, setTimeRange] = useState(30);

  // Fetch analytics data
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['analytics', 'overview', timeRange],
    queryFn: () => adminApi.getAnalyticsOverview(timeRange),
  });

  const { data: byUser, isLoading: byUserLoading } = useQuery({
    queryKey: ['analytics', 'by-user', timeRange],
    queryFn: () => adminApi.getAnalyticsByUser(timeRange),
  });

  const { data: byAgent, isLoading: byAgentLoading } = useQuery({
    queryKey: ['analytics', 'by-agent', timeRange],
    queryFn: () => adminApi.getAnalyticsByAgent(timeRange),
  });

  const { data: byModel, isLoading: byModelLoading } = useQuery({
    queryKey: ['analytics', 'by-model', timeRange],
    queryFn: () => adminApi.getAnalyticsByModel(timeRange),
  });

  const { data: overTime, isLoading: overTimeLoading } = useQuery({
    queryKey: ['analytics', 'over-time', timeRange],
    queryFn: () => adminApi.getAnalyticsOverTime(timeRange, timeRange <= 7 ? 'day' : 'day'),
  });

  const isLoading = overviewLoading || byUserLoading || byAgentLoading || byModelLoading || overTimeLoading;

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(amount);
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <MainLayout>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <CircularProgress />
        </Box>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <Box>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" fontWeight="700" gutterBottom>
              LLM Usage Analytics
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Monitor AI usage, costs, and adoption across your organization
            </Typography>
          </Box>

          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              label="Time Range"
            >
              <MenuItem value={7}>Last 7 days</MenuItem>
              <MenuItem value={30}>Last 30 days</MenuItem>
              <MenuItem value={90}>Last 90 days</MenuItem>
              <MenuItem value={180}>Last 6 months</MenuItem>
              <MenuItem value={365}>Last year</MenuItem>
            </Select>
          </FormControl>
        </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <TrendingUp sx={{ mr: 1, color: 'primary.main' }} />
                <Typography variant="body2" color="text.secondary" fontWeight="600">
                  Total API Calls
                </Typography>
              </Box>
              <Typography variant="h4" fontWeight="700">
                {formatNumber(overview?.total_stats?.total_calls || 0)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Successful LLM calls
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <AttachMoney sx={{ mr: 1, color: 'success.main' }} />
                <Typography variant="body2" color="text.secondary" fontWeight="600">
                  Total Cost
                </Typography>
              </Box>
              <Typography variant="h4" fontWeight="700">
                {formatCurrency(overview?.total_stats?.total_cost || 0)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Last {timeRange} days
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Memory sx={{ mr: 1, color: 'info.main' }} />
                <Typography variant="body2" color="text.secondary" fontWeight="600">
                  Total Tokens
                </Typography>
              </Box>
              <Typography variant="h4" fontWeight="700">
                {formatNumber(overview?.total_stats?.total_tokens || 0)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Input + Output tokens
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Speed sx={{ mr: 1, color: 'warning.main' }} />
                <Typography variant="body2" color="text.secondary" fontWeight="600">
                  Avg Latency
                </Typography>
              </Box>
              <Typography variant="h4" fontWeight="700">
                {overview?.total_stats?.avg_latency_ms
                  ? `${Math.round(overview.total_stats.avg_latency_ms)}ms`
                  : 'N/A'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Average response time
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Error Rate */}
      {overview?.error_stats && overview.error_stats.error_count > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="body2" fontWeight="600">
            Error Rate: {overview.error_stats.error_rate_percent}%
          </Typography>
          <Typography variant="body2">
            {overview.error_stats.error_count} failed calls out of {overview.error_stats.total_calls} total
          </Typography>
        </Alert>
      )}

      {/* Charts - Using Flexbox for better control */}
      <Box sx={{ mb: 2 }}>
        {/* Usage Over Time Chart - Full Width */}
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" fontWeight="600" gutterBottom>
              Usage Trend
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={overTime?.data || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" tickFormatter={formatDate} />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip
                  labelFormatter={formatDate}
                  formatter={(value, name) => {
                    if (name === 'total_cost') return [formatCurrency(value), 'Cost'];
                    if (name === 'call_count') return [formatNumber(value), 'Calls'];
                    return [formatNumber(value), name];
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="call_count"
                  stroke="#8884d8"
                  name="API Calls"
                  strokeWidth={2}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="total_cost"
                  stroke="#82ca9d"
                  name="Cost ($)"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Usage by Agent - Full Width */}
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight="600" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <SmartToy sx={{ mr: 1 }} />
              Usage by Agent
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={byAgent?.agents || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="agent_name" angle={-45} textAnchor="end" height={100} />
                <YAxis yAxisId="left" label={{ value: 'API Calls', angle: -90, position: 'insideLeft' }} />
                <YAxis yAxisId="right" orientation="right" label={{ value: 'Cost ($)', angle: 90, position: 'insideRight' }} />
                <Tooltip formatter={(value, name) => {
                  if (name === 'Cost ($)') return [formatCurrency(value), 'Cost'];
                  return [formatNumber(value), name];
                }} />
                <Legend />
                <Bar yAxisId="left" dataKey="call_count" fill="#82ca9d" name="API Calls" />
                <Bar yAxisId="right" dataKey="total_cost" fill="#8884d8" name="Cost ($)" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Box>

      {/* Usage by User Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight="600" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
            <Person sx={{ mr: 1 }} />
            Usage by User
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>User</TableCell>
                  <TableCell align="right">API Calls</TableCell>
                  <TableCell align="right">Total Tokens</TableCell>
                  <TableCell align="right">Input Tokens</TableCell>
                  <TableCell align="right">Output Tokens</TableCell>
                  <TableCell align="right">Total Cost</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(byUser?.users || []).map((user) => (
                  <TableRow key={user.user_id} hover>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight="600">
                          {user.full_name || user.email}
                        </Typography>
                        {user.full_name && (
                          <Typography variant="caption" color="text.secondary">
                            {user.email}
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      <Chip label={formatNumber(user.call_count)} size="small" color="primary" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">{formatNumber(user.total_tokens)}</TableCell>
                    <TableCell align="right">{formatNumber(user.input_tokens)}</TableCell>
                    <TableCell align="right">{formatNumber(user.output_tokens)}</TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" fontWeight="600" color="success.main">
                        {formatCurrency(user.total_cost)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
                {(!byUser?.users || byUser.users.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary">
                        No usage data available for this time period
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
      </Box>
    </MainLayout>
  );
}
