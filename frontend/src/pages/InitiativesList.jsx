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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  IconButton,
  Tooltip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
} from '@mui/material';
import {
  Search,
  Add,
  Visibility,
  PreviewOutlined,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { useInitiatives } from '../hooks/useInitiatives';
import MainLayout from '../layouts/MainLayout';


export default function InitiativesList() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [orderBy, setOrderBy] = useState('created_at');
  const [order, setOrder] = useState('desc');
  const [previewInitiative, setPreviewInitiative] = useState(null);

  const { data: initiatives, isLoading, error } = useInitiatives();

  // Filter and sort initiatives
  const filteredInitiatives = initiatives
    ?.filter((initiative) => {
      const matchesSearch = initiative.title
        .toLowerCase()
        .includes(searchTerm.toLowerCase()) ||
        initiative.description?.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesSearch;
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
            <TextField
              placeholder="Search initiatives..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              fullWidth
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
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
                  {searchTerm ? 'No initiatives found' : 'No initiatives yet'}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {searchTerm
                    ? 'Try adjusting your search'
                    : 'Create your first initiative to get started'}
                </Typography>
                {!searchTerm && (
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
                          active={orderBy === 'title'}
                          direction={orderBy === 'title' ? order : 'asc'}
                          onClick={() => handleSort('title')}
                        >
                          Name
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="center" sx={{ minWidth: 200 }}>
                        <TableSortLabel
                          active={orderBy === 'completion_percentage'}
                          direction={orderBy === 'completion_percentage' ? order : 'asc'}
                          onClick={() => handleSort('completion_percentage')}
                        >
                          Progress
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
                        <TableCell align="center">
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 150 }}>
                            <Box sx={{ flex: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={initiative.completion_percentage || 0}
                                sx={{
                                  height: 8,
                                  borderRadius: 1,
                                  backgroundColor: 'action.hover',
                                  '& .MuiLinearProgress-bar': {
                                    borderRadius: 1,
                                    backgroundColor:
                                      (initiative.completion_percentage || 0) === 100 ? 'success.main' :
                                      (initiative.completion_percentage || 0) >= 75 ? 'primary.main' :
                                      (initiative.completion_percentage || 0) >= 50 ? 'warning.main' : 'error.main'
                                  }
                                }}
                              />
                            </Box>
                            <Typography variant="body2" sx={{ minWidth: 40, fontWeight: 500 }}>
                              {initiative.completion_percentage || 0}%
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {new Date(initiative.created_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                            <Tooltip title="Preview">
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setPreviewInitiative(initiative);
                                }}
                              >
                                <PreviewOutlined fontSize="small" />
                              </IconButton>
                            </Tooltip>
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
                          </Box>
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

        {/* Preview Modal */}
        <Dialog
          open={Boolean(previewInitiative)}
          onClose={() => setPreviewInitiative(null)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            <Typography variant="h5" fontWeight="600">
              {previewInitiative?.title}
            </Typography>
          </DialogTitle>
          <DialogContent dividers>
            {/* Status Overview - At the top, prominent */}
            <Paper elevation={0} sx={{ bgcolor: 'action.hover', p: 3, mb: 3, borderRadius: 2 }}>
              <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                {/* Progress */}
                <Box sx={{ flex: '1 1 200px' }}>
                  <Typography variant="overline" color="text.secondary" fontWeight="600">
                    Progress
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                    <LinearProgress
                      variant="determinate"
                      value={previewInitiative?.completion_percentage || 0}
                      sx={{
                        flex: 1,
                        height: 10,
                        borderRadius: 1,
                        backgroundColor: 'background.paper',
                        '& .MuiLinearProgress-bar': {
                          borderRadius: 1,
                          backgroundColor:
                            (previewInitiative?.completion_percentage || 0) === 100 ? 'success.main' :
                            (previewInitiative?.completion_percentage || 0) >= 75 ? 'primary.main' :
                            (previewInitiative?.completion_percentage || 0) >= 50 ? 'warning.main' : 'error.main'
                        }
                      }}
                    />
                    <Typography variant="h6" fontWeight="600">
                      {previewInitiative?.completion_percentage || 0}%
                    </Typography>
                  </Box>
                </Box>

                {/* Created Date */}
                <Box>
                  <Typography variant="overline" color="text.secondary" fontWeight="600">
                    Created
                  </Typography>
                  <Typography variant="body1" sx={{ mt: 0.5 }}>
                    {previewInitiative?.created_at && new Date(previewInitiative.created_at).toLocaleDateString()}
                  </Typography>
                </Box>

                {/* Workflow Status */}
                <Box sx={{ flex: '1 1 100%' }}>
                  <Typography variant="overline" color="text.secondary" fontWeight="600" display="block" gutterBottom>
                    Workflow Status
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                    <Chip
                      label="Questions"
                      size="medium"
                      color={previewInitiative?.has_questions ? 'success' : 'default'}
                      variant={previewInitiative?.has_questions ? 'filled' : 'outlined'}
                    />
                    <Chip
                      label="Evaluation"
                      size="medium"
                      color={previewInitiative?.has_evaluation ? 'success' : 'default'}
                      variant={previewInitiative?.has_evaluation ? 'filled' : 'outlined'}
                    />
                    <Chip
                      label="MRD"
                      size="medium"
                      color={previewInitiative?.has_mrd ? 'success' : 'default'}
                      variant={previewInitiative?.has_mrd ? 'filled' : 'outlined'}
                    />
                    <Chip
                      label="Scored"
                      size="medium"
                      color={previewInitiative?.has_scores ? 'success' : 'default'}
                      variant={previewInitiative?.has_scores ? 'filled' : 'outlined'}
                    />
                  </Box>
                </Box>
              </Box>
            </Paper>

            {/* Description - With Markdown rendering */}
            <Box>
              <Typography variant="h6" gutterBottom fontWeight="600">
                Description
              </Typography>
              <Box
                sx={{
                  '& p': { mb: 2 },
                  '& h1, & h2, & h3, & h4, & h5, & h6': { mt: 2, mb: 1, fontWeight: 600 },
                  '& ul, & ol': { pl: 3, mb: 2 },
                  '& strong': { fontWeight: 600 },
                  '& code': {
                    bgcolor: 'action.hover',
                    px: 0.5,
                    py: 0.25,
                    borderRadius: 0.5,
                    fontFamily: 'monospace',
                    fontSize: '0.875em'
                  },
                  '& pre': {
                    bgcolor: 'action.hover',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto'
                  }
                }}
              >
                <ReactMarkdown>
                  {previewInitiative?.description || 'No description available'}
                </ReactMarkdown>
              </Box>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPreviewInitiative(null)}>
              Close
            </Button>
            <Button
              variant="contained"
              onClick={() => {
                setPreviewInitiative(null);
                navigate(`/initiatives/${previewInitiative?.id}`);
              }}
            >
              View Details
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </MainLayout>
  );
}
