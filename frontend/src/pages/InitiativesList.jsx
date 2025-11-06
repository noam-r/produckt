import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Chip,
  CircularProgress,
  Alert,
  Fab,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Search,
  Add,
  Visibility,
  FilterList,
} from '@mui/icons-material';
import { useInitiatives } from '../hooks/useInitiatives';
import MainLayout from '../layouts/MainLayout';

// Status options
const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'IN_DISCOVERY', label: 'In Discovery' },
  { value: 'IN_QA', label: 'In Q&A' },
  { value: 'READY_FOR_MRD', label: 'Ready for MRD' },
  { value: 'COMPLETED', label: 'Completed' },
];

// Status color mapping
const statusColors = {
  DRAFT: 'default',
  IN_DISCOVERY: 'info',
  IN_QA: 'warning',
  READY_FOR_MRD: 'secondary',
  COMPLETED: 'success',
};

export default function InitiativesList() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [orderBy, setOrderBy] = useState('created_at');
  const [order, setOrder] = useState('desc');

  const { data: initiatives, isLoading, error } = useInitiatives();

  // Filter and sort initiatives
  const filteredInitiatives = initiatives
    ?.filter((initiative) => {
      const matchesSearch = initiative.title
        .toLowerCase()
        .includes(searchTerm.toLowerCase()) ||
        initiative.description?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = !statusFilter || initiative.status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      const aValue = a[orderBy] || '';
      const bValue = b[orderBy] || '';

      if (order === 'asc') {
        return aValue > bValue ? 1 : -1;
      }
      return aValue < bValue ? 1 : -1;
    }) || [];

  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleRowClick = (id) => {
    navigate(`/initiatives/${id}`);
  };

  return (
    <MainLayout>
      <Box>
        {/* Header */}
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" fontWeight="600" gutterBottom>
              Initiatives
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Manage and track your product initiatives
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<Add />}
            size="large"
            onClick={() => navigate('/initiatives/new')}
          >
            New Initiative
          </Button>
        </Box>

        {/* Filters */}
        <Card elevation={2} sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                placeholder="Search initiatives..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                sx={{ flex: 1, minWidth: 250 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
              <FormControl sx={{ minWidth: 200 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={statusFilter}
                  label="Status"
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  {statusOptions.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </CardContent>
        </Card>

        {/* Table */}
        <Card elevation={2}>
          <CardContent>
            {isLoading && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
                <CircularProgress />
              </Box>
            )}

            {error && (
              <Alert severity="error">
                Failed to load initiatives: {error.message}
              </Alert>
            )}

            {!isLoading && !error && filteredInitiatives.length === 0 && (
              <Box sx={{ textAlign: 'center', py: 8 }}>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  {searchTerm || statusFilter ? 'No initiatives found' : 'No initiatives yet'}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {searchTerm || statusFilter
                    ? 'Try adjusting your filters'
                    : 'Create your first initiative to get started'}
                </Typography>
                {!searchTerm && !statusFilter && (
                  <Button
                    variant="outlined"
                    startIcon={<Add />}
                    sx={{ mt: 2 }}
                    onClick={() => navigate('/initiatives/new')}
                  >
                    Create Initiative
                  </Button>
                )}
              </Box>
            )}

            {!isLoading && !error && filteredInitiatives.length > 0 && (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>
                        <TableSortLabel
                          active={orderBy === 'name'}
                          direction={orderBy === 'name' ? order : 'asc'}
                          onClick={() => handleSort('name')}
                        >
                          Name
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>Description</TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={orderBy === 'status'}
                          direction={orderBy === 'status' ? order : 'asc'}
                          onClick={() => handleSort('status')}
                        >
                          Status
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>
                        <TableSortLabel
                          active={orderBy === 'created_at'}
                          direction={orderBy === 'created_at' ? order : 'asc'}
                          onClick={() => handleSort('created_at')}
                        >
                          Created
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredInitiatives.map((initiative) => (
                      <TableRow
                        key={initiative.id}
                        hover
                        sx={{
                          cursor: 'pointer',
                          '&:hover': {
                            bgcolor: 'action.hover',
                          },
                        }}
                        onClick={() => handleRowClick(initiative.id)}
                      >
                        <TableCell>
                          <Typography variant="body1" fontWeight="600">
                            {initiative.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              maxWidth: 300,
                            }}
                          >
                            {initiative.description || 'No description'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={initiative.status.replace('_', ' ')}
                            color={statusColors[initiative.status]}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {new Date(initiative.created_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="View Details">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRowClick(initiative.id);
                              }}
                            >
                              <Visibility fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {!isLoading && !error && filteredInitiatives.length > 0 && (
              <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2" color="text.secondary">
                  Showing {filteredInitiatives.length} of {initiatives?.length || 0} initiatives
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>

        {/* Floating Action Button for mobile */}
        <Fab
          color="primary"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            display: { xs: 'flex', md: 'none' },
          }}
          onClick={() => navigate('/initiatives/new')}
        >
          <Add />
        </Fab>
      </Box>
    </MainLayout>
  );
}
