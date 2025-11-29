# Vaadin to React Component Mapping

**Document Version**: 1.0
**Date**: 2025-11-28
**Purpose**: Guide for converting YAWL UI Vaadin components to React

---

## Executive Summary

This document maps Vaadin Flow components used in YAWL UI v5.2 to their React equivalents, with focus on:
- Component parity (UI widgets, layouts, forms)
- Event handling pattern conversion
- State management approaches
- Recommended React UI libraries

**Key Finding**: Material-UI (MUI) provides the closest component parity with Vaadin Flow, including Grid, Dialog, Form layouts, and DatePicker with minimal adapter code.

---

## 1. Component Mapping Table

### Core Form Components

| Vaadin Component | React Equivalent (MUI v5) | Alternative (Ant Design) | Notes |
|-----------------|---------------------------|-------------------------|-------|
| `TextField` | `TextField` | `Input` | Direct mapping, similar API |
| `Button` | `Button` | `Button` | Direct mapping |
| `ComboBox` | `Autocomplete` | `Select` | MUI Autocomplete handles search/filter |
| `DatePicker` | `DatePicker` (@mui/x-date-pickers) | `DatePicker` | Requires @mui/x-date-pickers addon |
| `Checkbox` | `Checkbox` | `Checkbox` | Direct mapping |
| `RadioButton` | `Radio` + `RadioGroup` | `Radio.Group` | Similar pattern |

**Example Conversion - TextField:**

```java
// Vaadin
private final TextField nameField = new TextField("Name");
nameField.setPlaceholder("Enter name");
nameField.setRequired(true);
nameField.addValueChangeListener(e -> handleNameChange(e.getValue()));
```

```jsx
// React + MUI
import { TextField } from '@mui/material';

function NameInput({ value, onChange }) {
  return (
    <TextField
      label="Name"
      placeholder="Enter name"
      required
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
```

### Data Display Components

| Vaadin Component | React Equivalent (MUI) | Alternative | Notes |
|-----------------|------------------------|------------|-------|
| `Grid<T>` | `DataGrid` (@mui/x-data-grid) | `Table` (Ant Design) | MUI DataGrid for advanced features, or basic `Table` |
| `TreeGrid` | `TreeView` + custom | `Tree` (Ant Design) | Requires custom cell rendering |
| `ListBox` | `List` + `ListItem` | `List` | Direct mapping |
| `Details` | `Accordion` | `Collapse` | Expandable content |

**Example Conversion - Grid:**

```java
// Vaadin
Grid<Participant> grid = new Grid<>();
grid.setItems(participants);
grid.addColumn(Participant::getUserId).setHeader("User ID");
grid.addColumn(Participant::getFullName).setHeader("Full Name");
grid.addComponentColumn(this::createActionButtons);
grid.setSelectionMode(Grid.SelectionMode.MULTI);
```

```jsx
// React + MUI DataGrid
import { DataGrid } from '@mui/x-data-grid';

function ParticipantGrid({ participants }) {
  const columns = [
    { field: 'userId', headerName: 'User ID', width: 150 },
    { field: 'fullName', headerName: 'Full Name', width: 200 },
    {
      field: 'actions',
      headerName: 'Actions',
      renderCell: (params) => <ActionButtons participant={params.row} />,
      sortable: false,
    },
  ];

  return (
    <DataGrid
      rows={participants}
      columns={columns}
      checkboxSelection
      getRowId={(row) => row.userId}
    />
  );
}
```

### Layout Components

| Vaadin Component | React Equivalent | CSS Approach | Notes |
|-----------------|-----------------|-------------|-------|
| `VerticalLayout` | `Stack` (MUI) | Flexbox `flex-direction: column` | MUI Stack recommended |
| `HorizontalLayout` | `Stack direction="row"` | Flexbox `flex-direction: row` | MUI Stack recommended |
| `FormLayout` | `Grid` (MUI) + custom | CSS Grid | Requires responsive breakpoints |
| `Div` | `Box` (MUI) | `<div>` | Box provides system props |
| `AppLayout` | Custom layout | Material-UI `Drawer` + `AppBar` | Build with drawer + header |

**Example Conversion - Layouts:**

```java
// Vaadin
VerticalLayout layout = new VerticalLayout();
layout.setAlignItems(FlexComponent.Alignment.CENTER);
layout.add(logo, loginForm);
layout.setSizeFull();
```

```jsx
// React + MUI
import { Stack } from '@mui/material';

function LoginLayout({ logo, loginForm }) {
  return (
    <Stack
      alignItems="center"
      justifyContent="center"
      sx={{ width: '100%', height: '100vh' }}
    >
      {logo}
      {loginForm}
    </Stack>
  );
}
```

### Dialog and Notification Components

| Vaadin Component | React Equivalent (MUI) | Notes |
|-----------------|------------------------|-------|
| `Dialog` | `Dialog` | Direct mapping |
| `Notification` | `Snackbar` + `Alert` | MUI Snackbar for toast-style notifications |
| `ConfirmDialog` | `Dialog` + custom buttons | Build with Dialog + Button actions |

**Example Conversion - Dialog:**

```java
// Vaadin
Dialog dialog = new Dialog();
dialog.setHeaderTitle("Confirm Action");
dialog.add(new Text("Are you sure?"));
Button confirm = new Button("Confirm", e -> {
    performAction();
    dialog.close();
});
dialog.getFooter().add(confirm);
dialog.open();
```

```jsx
// React + MUI
import { Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';

function ConfirmDialog({ open, onClose, onConfirm }) {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Confirm Action</DialogTitle>
      <DialogContent>Are you sure?</DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={() => { onConfirm(); onClose(); }}>
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

### File Upload Component

| Vaadin Component | React Equivalent | Notes |
|-----------------|-----------------|-------|
| `Upload` | Custom + `<input type="file">` | Use react-dropzone or MUI Button + input |

**Example Conversion - Upload:**

```java
// Vaadin
Upload upload = new Upload(receiver);
upload.setAcceptedFileTypes(".yawl", ".xml");
upload.addSucceededListener(e -> handleFileUpload(e.getFileName()));
```

```jsx
// React + react-dropzone
import { useDropzone } from 'react-dropzone';
import { Button } from '@mui/material';

function FileUpload({ onUpload }) {
  const { getRootProps, getInputProps } = useDropzone({
    accept: {
      'application/xml': ['.yawl', '.xml']
    },
    onDrop: (acceptedFiles) => {
      acceptedFiles.forEach(file => onUpload(file));
    }
  });

  return (
    <div {...getRootProps()}>
      <input {...getInputProps()} />
      <Button variant="contained">Upload Specification</Button>
    </div>
  );
}
```

---

## 2. Event Handling Pattern Conversion

### Vaadin Event Listeners → React Hooks

**Pattern 1: Value Change Listeners → onChange**

```java
// Vaadin - Listener pattern
TextField field = new TextField();
field.addValueChangeListener(e -> {
    String newValue = e.getValue();
    updateState(newValue);
});
```

```jsx
// React - useState + onChange
import { useState } from 'react';
import { TextField } from '@mui/material';

function FormField() {
  const [value, setValue] = useState('');

  const handleChange = (e) => {
    const newValue = e.target.value;
    setValue(newValue);
    // Additional state update logic
  };

  return <TextField value={value} onChange={handleChange} />;
}
```

**Pattern 2: Click Listeners → onClick**

```java
// Vaadin
Button button = new Button("Save", e -> {
    saveData();
    showNotification("Saved");
});
```

```jsx
// React
import { Button, Snackbar } from '@mui/material';
import { useState } from 'react';

function SaveButton({ onSave }) {
  const [showNotif, setShowNotif] = useState(false);

  const handleClick = () => {
    onSave();
    setShowNotif(true);
  };

  return (
    <>
      <Button onClick={handleClick}>Save</Button>
      <Snackbar
        open={showNotif}
        autoHideDuration={3000}
        onClose={() => setShowNotif(false)}
        message="Saved"
      />
    </>
  );
}
```

**Pattern 3: Grid Selection → DataGrid callbacks**

```java
// Vaadin
grid.addSelectionListener(e -> {
    Set<Participant> selected = e.getAllSelectedItems();
    updateSelection(selected);
});
```

```jsx
// React + MUI DataGrid
import { DataGrid } from '@mui/x-data-grid';

function ParticipantGrid({ participants }) {
  const [selected, setSelected] = useState([]);

  const handleSelectionChange = (newSelection) => {
    setSelected(newSelection);
    // Additional logic
  };

  return (
    <DataGrid
      rows={participants}
      columns={columns}
      checkboxSelection
      onRowSelectionModelChange={handleSelectionChange}
      rowSelectionModel={selected}
    />
  );
}
```

---

## 3. State Management Recommendations

### Vaadin Server-Side State → React Client-Side State

| Vaadin Pattern | React Equivalent | When to Use |
|---------------|-----------------|------------|
| Component fields (`private TextField field`) | `useState` hook | Local component state |
| Session attributes | React Context | Global app state (user session) |
| Binder (form binding) | React Hook Form / Formik | Complex forms with validation |
| Grid data provider | `useState` + API calls | Server-side pagination |

**Example: Form State Management**

```java
// Vaadin - Binder pattern
public class ProfileView extends Div {
    private Binder<Participant> binder = new Binder<>(Participant.class);
    private TextField firstName = new TextField("First Name");

    public ProfileView(Participant participant) {
        binder.forField(firstName)
              .asRequired("Required")
              .bind(Participant::getFirstName, Participant::setFirstName);
        binder.setBean(participant);
    }
}
```

```jsx
// React - React Hook Form
import { useForm } from 'react-hook-form';
import { TextField, Button } from '@mui/material';

function ProfileView({ participant }) {
  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: {
      firstName: participant.firstName,
      lastName: participant.lastName,
    }
  });

  const onSubmit = (data) => {
    // API call to save participant
    updateParticipant(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <TextField
        label="First Name"
        {...register('firstName', { required: 'Required' })}
        error={!!errors.firstName}
        helperText={errors.firstName?.message}
      />
      <Button type="submit">Save</Button>
    </form>
  );
}
```

**Global State (User Session)**

```java
// Vaadin - Session attribute
VaadinSession.getCurrent().setAttribute("user", participant);
```

```jsx
// React - Context API
import { createContext, useContext, useState } from 'react';

const UserContext = createContext();

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);

  return (
    <UserContext.Provider value={{ user, setUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}

// Usage in component
function ProfileView() {
  const { user } = useUser();
  return <div>Welcome, {user.firstName}</div>;
}
```

---

## 4. Dynamic Form Generation (DynForm System)

The YAWL DynForm system dynamically generates forms from XML schema. React equivalent:

### Vaadin DynForm Approach

```java
public class DynFormFactory {
    public DynFormLayout createForm(String schema, WorkItemRecord wir) {
        // Parse schema, generate fields
        List<DynFormField> fields = fieldAssembler.getFieldList();
        for (DynFormField field : fields) {
            Component component = builder.makeInputField(field);
            layout.add(component);
        }
        return layout;
    }
}
```

### React Dynamic Form Approach

```jsx
import { TextField, Select, MenuItem, Checkbox } from '@mui/material';

function DynamicForm({ schema, data }) {
  const [formData, setFormData] = useState(data);

  const renderField = (field) => {
    const { name, type, label, required } = field;

    switch (type) {
      case 'string':
        return (
          <TextField
            key={name}
            label={label}
            required={required}
            value={formData[name] || ''}
            onChange={(e) => setFormData({
              ...formData,
              [name]: e.target.value
            })}
          />
        );
      case 'boolean':
        return (
          <Checkbox
            key={name}
            checked={formData[name] || false}
            onChange={(e) => setFormData({
              ...formData,
              [name]: e.target.checked
            })}
          />
        );
      case 'select':
        return (
          <Select
            key={name}
            value={formData[name] || ''}
            onChange={(e) => setFormData({
              ...formData,
              [name]: e.target.value
            })}
          >
            {field.options.map(opt => (
              <MenuItem key={opt.value} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
          </Select>
        );
      default:
        return null;
    }
  };

  const fields = parseSchema(schema); // Parse XML schema to field definitions

  return (
    <form>
      {fields.map(renderField)}
    </form>
  );
}

// Schema parser (simplified)
function parseSchema(xsdSchema) {
  // Parse XSD to JSON field definitions
  // Returns: [{ name: 'field1', type: 'string', label: 'Field 1', required: true }, ...]
  const parser = new XSDParser();
  return parser.parse(xsdSchema);
}
```

**Recommended Libraries for Dynamic Forms:**
- **react-jsonschema-form** - Generate forms from JSON Schema (convert XSD → JSON Schema)
- **formik + yup** - Dynamic validation schemas
- **react-hook-form** - Performance-optimized form state

---

## 5. Recommended React UI Library

### Primary Recommendation: Material-UI (MUI) v5

**Reasons:**
1. **Component Parity**: Closest match to Vaadin Flow components (Grid, Dialog, Form layouts)
2. **DataGrid**: MUI X DataGrid provides advanced features (sorting, filtering, pagination) similar to Vaadin Grid
3. **Theming**: Comprehensive theming system similar to Vaadin's Lumo theme
4. **TypeScript Support**: Full TypeScript definitions (important for type-safe migration)
5. **Active Development**: Well-maintained, large community

**Installation:**
```bash
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/x-data-grid  # For advanced Grid features
npm install @mui/x-date-pickers @date-fns/date-fns  # For DatePicker
```

**Basic Setup:**

```jsx
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2', // YAWL blue
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {/* Your app components */}
    </ThemeProvider>
  );
}
```

### Alternative: Ant Design

**When to Use:**
- Prefer more opinionated design system
- Need enterprise-grade components out-of-box
- Want Chinese internationalization support

**Component Mapping Differences:**
- `Table` instead of DataGrid (simpler, but less feature-rich)
- `Form` component with built-in validation
- Different layout approach (Grid system vs Flexbox)

---

## 6. Routing and Navigation

### Vaadin Flow Router → React Router

```java
// Vaadin - @Route annotation
@Route("worklist")
public class WorklistView extends VerticalLayout {
    // View implementation
}
```

```jsx
// React - React Router v6
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/worklist" element={<WorklistView />} />
        <Route path="/profile" element={<ProfileView />} />
        <Route path="/cases" element={<CasesView />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### Vaadin Navigation → React Router Navigation

```java
// Vaadin
UI.getCurrent().navigate(WorklistView.class);
```

```jsx
// React
import { useNavigate } from 'react-router-dom';

function NavigationButton() {
  const navigate = useNavigate();
  return <Button onClick={() => navigate('/worklist')}>Worklist</Button>;
}
```

---

## 7. Server Communication

### Vaadin Server Calls → React API Calls

```java
// Vaadin - Direct service calls (server-side)
ResourceClient client = Clients.getResourceClient();
List<Participant> participants = client.getParticipants();
grid.setItems(participants);
```

```jsx
// React - Fetch API or Axios
import { useState, useEffect } from 'react';
import axios from 'axios';

function ParticipantList() {
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('/api/participants')
      .then(response => {
        setParticipants(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching participants', error);
        setLoading(false);
      });
  }, []);

  if (loading) return <CircularProgress />;

  return <DataGrid rows={participants} columns={columns} />;
}
```

**Recommended Approach: React Query**

```jsx
import { useQuery } from '@tanstack/react-query';

function ParticipantList() {
  const { data: participants, isLoading, error } = useQuery({
    queryKey: ['participants'],
    queryFn: () => axios.get('/api/participants').then(res => res.data)
  });

  if (isLoading) return <CircularProgress />;
  if (error) return <Alert severity="error">Error loading data</Alert>;

  return <DataGrid rows={participants} columns={columns} />;
}
```

---

## 8. Authentication and Security

### Vaadin Security → React Auth Patterns

```java
// Vaadin - Login view with authentication
LoginForm login = new LoginForm();
login.addLoginListener(e -> {
    if (resourceClient.authenticate(e.getUsername(), e.getPassword())) {
        UI.getCurrent().navigate(WorklistView.class);
    } else {
        login.setError(true);
    }
});
```

```jsx
// React - Login with Context
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TextField, Button, Alert } from '@mui/material';
import { useUser } from './UserContext';

function LoginView() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(false);
  const { setUser } = useUser();
  const navigate = useNavigate();

  const handleLogin = async () => {
    try {
      const response = await axios.post('/api/auth/login', {
        username,
        password
      });
      setUser(response.data.user);
      navigate('/worklist');
    } catch (err) {
      setError(true);
    }
  };

  return (
    <form onSubmit={(e) => { e.preventDefault(); handleLogin(); }}>
      {error && <Alert severity="error">Invalid credentials</Alert>}
      <TextField
        label="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <TextField
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <Button type="submit">Login</Button>
    </form>
  );
}
```

**Protected Routes:**

```jsx
function ProtectedRoute({ children }) {
  const { user } = useUser();

  if (!user) {
    return <Navigate to="/login" />;
  }

  return children;
}

// Usage
<Route path="/worklist" element={
  <ProtectedRoute>
    <WorklistView />
  </ProtectedRoute>
} />
```

---

## 9. Migration Strategy

### Phased Approach

**Phase 1: Core Components (Weeks 1-2)**
- Set up React + MUI project structure
- Implement authentication (login/logout)
- Create main layout (AppBar, Drawer navigation)
- Build UserContext for session management

**Phase 2: Data Grids (Weeks 3-4)**
- Convert Participant grid view
- Convert Cases grid view
- Implement server-side pagination
- Add sorting/filtering

**Phase 3: Forms (Weeks 5-6)**
- Convert Profile form
- Implement form validation
- Build reusable form components
- DynForm prototype (XML schema → React form)

**Phase 4: Dialogs and Actions (Weeks 7-8)**
- Convert all dialog components
- Implement notifications/snackbars
- Add confirmation dialogs
- File upload functionality

**Phase 5: Advanced Features (Weeks 9-10)**
- Calendar view
- TreeGrid components
- Custom components
- Polish and optimization

### Code Structure Recommendation

```
src/
├── components/
│   ├── common/           # Reusable UI components
│   │   ├── DataGrid.jsx
│   │   ├── FormField.jsx
│   │   └── ConfirmDialog.jsx
│   ├── layout/           # Layout components
│   │   ├── AppLayout.jsx
│   │   ├── Sidebar.jsx
│   │   └── Header.jsx
│   └── forms/            # Form components
│       ├── DynamicForm.jsx
│       └── ProfileForm.jsx
├── views/                # Page views
│   ├── WorklistView.jsx
│   ├── ParticipantsView.jsx
│   └── CasesView.jsx
├── context/              # React contexts
│   ├── UserContext.jsx
│   └── NotificationContext.jsx
├── hooks/                # Custom hooks
│   ├── useAuth.js
│   └── useApi.js
├── services/             # API services
│   ├── resourceClient.js
│   └── engineClient.js
└── utils/                # Utilities
    ├── schemaParser.js   # XSD to JSON schema
    └── validators.js
```

---

## 10. Performance Considerations

### Vaadin Server-Side Rendering → React Client-Side Rendering

**Key Differences:**
- Vaadin: Server maintains component state, DOM updates via WebSocket
- React: Client manages state, DOM updates via Virtual DOM

**Optimization Strategies:**

1. **Lazy Loading:**
```jsx
import { lazy, Suspense } from 'react';

const WorklistView = lazy(() => import('./views/WorklistView'));

function App() {
  return (
    <Suspense fallback={<CircularProgress />}>
      <WorklistView />
    </Suspense>
  );
}
```

2. **Memoization:**
```jsx
import { memo, useMemo } from 'react';

const ParticipantRow = memo(({ participant }) => {
  // Component only re-renders if participant changes
  return <div>{participant.fullName}</div>;
});

function ParticipantList({ participants }) {
  const sortedParticipants = useMemo(
    () => participants.sort((a, b) => a.fullName.localeCompare(b.fullName)),
    [participants]
  );

  return sortedParticipants.map(p => <ParticipantRow key={p.id} participant={p} />);
}
```

3. **Virtual Scrolling (for large grids):**
```jsx
import { DataGrid } from '@mui/x-data-grid';

function LargeParticipantGrid({ participants }) {
  return (
    <DataGrid
      rows={participants}
      columns={columns}
      pagination
      pageSize={50}
      virtualization  // Enable virtual scrolling
    />
  );
}
```

---

## 11. Testing Recommendations

### Vaadin TestBench → React Testing Library

```java
// Vaadin TestBench
@Test
public void testLogin() {
    LoginFormElement loginForm = $(LoginFormElement.class).first();
    loginForm.getUsernameField().setValue("admin");
    loginForm.getPasswordField().setValue("password");
    loginForm.submit();
    Assert.assertTrue($(WorklistViewElement.class).exists());
}
```

```jsx
// React Testing Library
import { render, screen, fireEvent } from '@testing-library/react';
import { LoginView } from './LoginView';

test('successful login navigates to worklist', async () => {
  render(<LoginView />);

  fireEvent.change(screen.getByLabelText('Username'), {
    target: { value: 'admin' }
  });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'password' }
  });

  fireEvent.click(screen.getByRole('button', { name: 'Login' }));

  await screen.findByText('Worklist'); // Verify navigation
});
```

---

## 12. Summary and Recommendations

### Key Takeaways

1. **Use Material-UI (MUI)** as primary UI library for closest Vaadin parity
2. **React Hook Form** for complex form validation (replaces Vaadin Binder)
3. **React Query** for server state management (replaces Vaadin data providers)
4. **React Router v6** for navigation (replaces Vaadin Flow Router)
5. **Context API** for global state (replaces VaadinSession)

### Architectural Changes

| Vaadin Approach | React Approach | Impact |
|----------------|---------------|--------|
| Server-side state | Client-side state (useState, Context) | More network calls, better UX |
| Component tree managed by server | Virtual DOM diffing | Better performance |
| Java type safety | TypeScript (recommended) | Maintain type safety |
| Built-in validation | react-hook-form + yup | Explicit validation schemas |

### Next Steps

1. **Prototype** one complex view (e.g., Worklist) to validate approach
2. **Define API contracts** between React frontend and Python backend
3. **Set up CI/CD** for React app (separate from YAWL engine)
4. **Plan data migration** if needed (authentication, sessions)
5. **Create component library** of reusable YAWL-specific components

---

## Appendix A: Complete Component Mapping Reference

| Vaadin | MUI v5 | Ant Design | Plain React |
|--------|--------|-----------|------------|
| TextField | TextField | Input | `<input>` |
| Button | Button | Button | `<button>` |
| ComboBox | Autocomplete | Select | `<select>` + filter logic |
| DatePicker | DatePicker (@mui/x-date-pickers) | DatePicker | react-datepicker |
| Grid | DataGrid (@mui/x-data-grid) | Table | react-table |
| TreeGrid | TreeView + custom | Tree | Custom recursion |
| Dialog | Dialog | Modal | Custom overlay |
| Notification | Snackbar + Alert | notification API | Custom toast |
| Upload | Custom + dropzone | Upload | `<input type="file">` |
| FormLayout | Grid | Form | CSS Grid |
| VerticalLayout | Stack | Space direction="vertical" | Flexbox column |
| HorizontalLayout | Stack direction="row" | Space | Flexbox row |
| AppLayout | Custom (Drawer + AppBar) | Layout | Custom |
| Tabs | Tabs | Tabs | Custom |
| Accordion | Accordion | Collapse | Custom |
| Checkbox | Checkbox | Checkbox | `<input type="checkbox">` |
| RadioButton | Radio + RadioGroup | Radio.Group | `<input type="radio">` |
| ProgressBar | LinearProgress | Progress | Custom |
| Icon | Icon (MUI Icons) | Icon | react-icons |

---

## Appendix B: Resources

### Documentation
- [Material-UI Documentation](https://mui.com/material-ui/getting-started/)
- [MUI X DataGrid](https://mui.com/x/react-data-grid/)
- [React Hook Form](https://react-hook-form.com/)
- [React Router](https://reactrouter.com/)
- [React Query](https://tanstack.com/query/latest)

### Example Projects
- [MUI Templates](https://mui.com/material-ui/getting-started/templates/)
- [React Admin](https://marmelab.com/react-admin/) - Similar to Vaadin admin UIs

### Migration Tools
- [XSD to JSON Schema Converter](https://www.liquid-technologies.com/online-xsd-to-json-schema-converter)
- [react-jsonschema-form](https://rjsf-team.github.io/react-jsonschema-form/)

---

**End of Document**
