document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT ---
    const appState = { isLoggedIn: false, userName: '', userId: '', userRole: 'user', authCheckInterval: null };

    // --- DOM ELEMENTS ---
    const pages = {
        login: document.getElementById('login-page'),
        dashboard: document.getElementById('dashboard-page'),
        transaction: document.getElementById('transaction-page'),
        adminAuth: document.getElementById('admin-auth-page'),
        adminDashboard: document.getElementById('admin-dashboard-page'),
        forgotPassword: document.getElementById('forgot-password-page')
    };

    const userControls = document.getElementById('user-controls');
    const welcomeMessage = document.getElementById('welcome-message');
    const loginForm = document.getElementById('login-form');
    const logoutBtn = document.getElementById('logout-btn');
    const gotoBorrowBtn = document.getElementById('goto-borrow-btn');
    const gotoReturnBtn = document.getElementById('goto-return-btn');
    const backBtns = document.querySelectorAll('.back-btn');
    const authStep = document.getElementById('auth-step');
    const bookStep = document.getElementById('book-step');
    const authSpinner = document.querySelector('#auth-step .spinner');
    const authMessage = document.getElementById('auth-message');
    const transactionTitle = document.getElementById('transaction-title');
    const transactionTypeSpan = document.getElementById('transaction-type');
    const bookIdInput = document.getElementById('book-id-input');
    const confirmTransactionBtn = document.getElementById('confirm-transaction-btn');
    const transactionStatus = document.getElementById('transaction-status');
    const scanBtn = document.getElementById('scan-btn');
    const stopScanBtn = document.getElementById('stop-scan-btn');
    const scannerContainer = document.getElementById('scanner-container');
    const historyAccordionContainer = document.getElementById('history-accordion-container');
    const chatWidget = document.getElementById('chat-widget');
    const adminLogoutBtn = document.getElementById('admin-logout-btn');
    const adminDashboardLogoutBtn = document.getElementById('admin-dashboard-logout-btn');
    const adminWelcomeMessage = document.getElementById('admin-welcome-message');
    
    const paymentAlertContainer = document.getElementById('payment-alert-container');

    // Dashboard Tabs
    const tabBooksBtn = document.getElementById('tab-books');
    const tabRecsBtn = document.getElementById('tab-recommendations');
    const tabSettingsBtn = document.getElementById('tab-settings');
    const contentBooks = document.getElementById('content-books');
    const contentRecs = document.getElementById('content-recommendations');
    const contentSettings = document.getElementById('content-settings');

    // Password Forms
    const gotoForgotPasswordBtn = document.getElementById('goto-forgot-password-btn');
    const gotoLoginBtn = document.getElementById('goto-login-btn');
    const forgotPasswordForm = document.getElementById('forgot-password-form');
    const forgotPasswordStatus = document.getElementById('forgot-password-status');
    const changePasswordForm = document.getElementById('change-password-form');
    const changePasswordStatus = document.getElementById('change-password-status');

    // --- ADMIN ELEMENTS ---
    const adminTabs = document.querySelectorAll('.admin-tab-button');
    const adminTabContents = document.querySelectorAll('.admin-tab-content');
    const adminDueDateAlertsList = document.getElementById('due-date-alerts-list');
    const allBorrowedBooksList = document.getElementById('all-borrowed-books-list');
    const addBookForm = document.getElementById('add-book-form');
    const addUserForm = document.getElementById('add-user-form');
    const removeUserForm = document.getElementById('remove-user-form');
    const reissueRfidForm = document.getElementById('reissue-rfid-form');
    const searchBookInput = document.getElementById('search-book-input');
    const searchBookResults = document.getElementById('search-book-results');
    const addBookStatus = document.getElementById('add-book-status');
    const addUserStatus = document.getElementById('add-user-status');
    const removeUserStatus = document.getElementById('remove-user-status');
    const reissueRfidStatus = document.getElementById('reissue-rfid-status');

    // --- CHATBOT ELEMENTS ---
    const chatWindow = document.getElementById('chat-window');
    const chatToggleBtn = document.getElementById('chat-toggle-btn');
    const chatIconOpen = document.getElementById('chat-icon-open');
    const chatIconClose = document.getElementById('chat-icon-close');
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');

    // --- API HELPER ---
    const api = {
        async request(endpoint, options = {}) {
            try {
                const response = await fetch(`/api${endpoint}`, options);
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || errorData.error || 'An error occurred');
                }
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.indexOf("application/json") !== -1) {
                    return await response.json();
                } else {
                    return {}; 
                }
            } catch (error) {
                console.error(`API Error on ${endpoint}:`, error);
                throw error;
            }
        },
        login: (userId, password) => api.request('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId, password })
        }),
        logout: () => api.request('/logout', { method: 'POST' }),
        checkAuthStatus: () => api.request('/user/status'),
        getDashboard: () => api.request('/user/dashboard'),
        borrowBook: (bookId) => api.request('/book/borrow', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bookId })
        }),
        returnBook: (bookId) => api.request('/book/return', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bookId })
        }),
        askChatbot: (message) => api.request('/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        }),
        getAdminDashboardData: () => api.request('/admin/dashboard_data'),
        addBook: (data) => api.request('/admin/add_book', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
        addUser: (data) => api.request('/admin/add_user', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
        removeUser: (userId) => api.request('/admin/remove_user', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: userId }) }),
        searchBook: (searchTerm) => api.request('/admin/search_book', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ search_term: searchTerm }) }),
        reissueRfid: (data) => api.request('/admin/reissue_rfid', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
        
        paypalCreateOrder: () => api.request('/paypal/create_order', {
            method: 'POST'
        }),
        paypalCaptureOrder: (orderID) => api.request('/paypal/capture_order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ orderID })
        }),
        
        // **NEW**: API endpoint for deauthorizing
        deauthorize: () => api.request('/user/deauthorize', { method: 'POST' }),
        
        changePassword: (old_password, new_password) => api.request('/user/change_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_password, new_password })
        }),
        forgotPassword: (user_id, email, new_password) => api.request('/forgot_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id, email, new_password })
        })
    };

    // --- UI MANAGEMENT ---
    const ui = {
        showPage(pageId) {
            Object.values(pages).forEach(page => page?.classList.add('hidden'));
            if (pages[pageId]) pages[pageId].classList.remove('hidden');
        },
        showDashboard() {
            if (appState.userRole === 'admin') {
                this.showPage('adminDashboard');
                this.renderAdminDashboard();
            } else {
                this.showPage('dashboard');
                this.renderUserDashboard();
            }
        },
        updateLoginState() {
            if (appState.isLoggedIn) {
                if (appState.userRole === 'admin') {
                    adminWelcomeMessage.textContent = `Welcome, Admin ${appState.userName}!`;
                    if (userControls) userControls.classList.add('hidden');
                    if (chatWidget) chatWidget.classList.add('hidden');
                } else {
                    userControls.classList.remove('hidden');
                    welcomeMessage.textContent = `Welcome, ${appState.userName}!`;
                    chatWidget.classList.remove('hidden');
                    this.showPage('dashboard');
                    this.renderUserDashboard();
                }
            } else {
                Object.values(pages).forEach(page => page?.classList.add('hidden'));
                pages.login.classList.remove('hidden');
                if (userControls) userControls.classList.add('hidden');
                if (chatWidget) chatWidget.classList.add('hidden');
            }
        },
        async renderUserDashboard() {
            try {
                const dashData = await api.getDashboard();
                
                const currentList = document.getElementById('current-books-list');
                const historyList = document.getElementById('history-books-list');
                const recommendationsList = document.getElementById('recommendations-list');
                
                const totalFine = dashData.total_fine;

                // Helper function to create book cards
                const createBookCard = (book) => {
                    const dueDate = new Date(book.due_date);
                    const predictionPercent = book.late_prediction_percent || 0;
                    
                    let statusTileHtml = '';
                    
                    if (book.is_overdue) {
                        if (book.current_fine > 0) {
                            // 1. OVERDUE TILE
                            statusTileHtml = `
                                <div class="p-2 rounded-lg bg-red-100 dark:bg-red-900 dark:bg-opacity-40 text-center">
                                    <div class="text-xs font-medium text-red-600 dark:text-red-300">STATUS</div>
                                    <div class="text-lg font-bold text-red-700 dark:text-red-200">OVERDUE</div>
                                    <div class="text-sm font-semibold text-red-700 dark:text-red-200 mt-1">Fine: $${book.current_fine.toFixed(2)}</div>
                                </div>`;
                        } else {
                            // 2. FINE PAID TILE
                            statusTileHtml = `
                                <div class="p-2 rounded-lg bg-green-100 dark:bg-green-900 dark:bg-opacity-40 text-center">
                                    <div class="text-xs font-medium text-green-600 dark:text-green-300">STATUS</div>
                                    <div class="text-lg font-bold text-green-700 dark:text-green-200">FINE PAID</div>
                                    <div class="text-sm text-green-700 dark:text-green-200 mt-1">Overdue</div>
                                </div>`;
                        }
                    } else {
                        // 3. RISK PREDICTION TILE
                        let riskColor, riskText;
                        if (predictionPercent > 70) {
                            riskColor = 'red'; riskText = 'High Risk';
                        } else if (predictionPercent > 40) {
                            riskColor = 'yellow'; riskText = 'Medium Risk';
                        } else {
                            riskColor = 'green'; riskText = 'Low Risk';
                        }
                        
                        statusTileHtml = `
                            <div class="p-2 rounded-lg bg-${riskColor}-100 dark:bg-${riskColor}-900 dark:bg-opacity-40 text-center">
                                <div class="text-xs font-medium text-${riskColor}-600 dark:text-${riskColor}-300">LATE RISK</div>
                                <div class="text-lg font-bold text-${riskColor}-700 dark:text-${riskColor}-200">${predictionPercent}%</div>
                                <div class="text-sm font-semibold text-${riskColor}-700 dark:text-${riskColor}-200 mt-1">${riskText}</div>
                            </div>`;
                    }

                    return `
                    <div class="flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
                        <img src="${book.image_url || '/static/images/placeholder.jpg'}" 
                             alt="Cover of ${book.title}" 
                             class="w-20 h-28 object-cover rounded shadow-md bg-slate-200 dark:bg-gray-600"
                             onerror="this.onerror=null; this.src='/static/images/placeholder.jpg';">
                        
                        <div class="flex-grow">
                            <div class="font-bold text-lg text-slate-800 dark:text-white">${book.title}</div>
                            <div class="text-sm text-slate-500 dark:text-gray-400 mb-2">by ${book.author}</div>
                            <div class="text-sm text-slate-600 dark:text-gray-300">
                                Due: <span class="font-semibold">${dueDate.toLocaleDateString()}</span>
                            </div>
                        </div>

                        <div class="w-28 flex-shrink-0">
                            ${statusTileHtml}
                        </div>
                    </div>`;
                };

                // Render Current Books
                if (currentList && Array.isArray(dashData.current_books)) {
                    currentList.innerHTML = dashData.current_books.length
                        ? dashData.current_books.map(createBookCard).join('')
                        : '<p class="text-slate-500 dark:text-gray-400 text-sm p-4 text-center">No books currently on loan.</p>';
                }
                
                // Render Payment Alert Box
                paymentAlertContainer.innerHTML = '';
                paymentAlertContainer.className = '';
                if (totalFine > 0) {
                    renderPaymentAlert(totalFine);
                }

                // Render History Books
                if (historyList && Array.isArray(dashData.history_books)) {
                    historyAccordionContainer.classList.toggle('hidden', dashData.history_books.length === 0);
                    historyList.innerHTML = dashData.history_books.length
                        ? dashData.history_books.map(book => `
                            <div class="flex items-center gap-4 p-4 border-t border-gray-200 dark:border-gray-600">
                                <img src="${book.image_url || '/static/images/placeholder.jpg'}" 
                                     alt="Cover of ${book.title}" 
                                     class="w-12 h-16 object-cover rounded shadow bg-slate-200 dark:bg-gray-600"
                                     onerror="this.onerror=null; this.src='/static/images/placeholder.jpg';">
                                <div>
                                    <div class="font-semibold text-slate-800 dark:text-white">${book.title}</div>
                                    <div class="text-sm text-slate-500 dark:text-gray-400">by ${book.author}</div>
                                </div>
                                <div class="ml-auto text-sm text-slate-500 dark:text-gray-400 text-right">
                                    Returned: <br> <span class="font-medium">${new Date(book.return_date).toLocaleDateString()}</span>
                                </div>
                            </div>
                        `).join('')
                        : '';
                }

                // Render Recommendations
                let seedBookId = dashData.current_books?.[0]?.book_id || dashData.history_books?.[0]?.book_id || 'default';
                const recData = await api.request(`/recommendations/${seedBookId}`);
                if (recommendationsList && Array.isArray(recData.recommendations)) {
                    recommendationsList.innerHTML = recData.recommendations.length
                        ? recData.recommendations.map(book => {
                            return `
                            <div class="space-y-2 bg-gray-50 dark:bg-gray-700 p-3 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                <img src="${book.image_url || '/static/images/placeholder.jpg'}" 
                                     alt="Cover of ${book.title}" 
                                     class="w-full h-auto aspect-[2/3] object-cover rounded-md shadow-md bg-slate-200 dark:bg-gray-600" 
                                     onerror="this.onerror=null; this.src='/static/images/placeholder.jpg';"
                                     onload="if (this.naturalWidth <= 1) { this.src='/static/images/placeholder.jpg'; }">
                                <div class="text-sm font-semibold text-slate-800 dark:text-white truncate" title="${book.title}">${book.title}</div>
                                <div class="text-xs text-slate-500 dark:text-gray-400 truncate" title="${book.author}">${book.author}</div>
                            </div>`;
                        }).join('')
                        : '<p class="text-slate-500 dark:text-gray-400 text-sm col-span-full text-center">No recommendations available.</p>';
                }
                
            } catch (error) {
                console.error("Error during renderDashboard:", error);
                alert('Could not load dashboard data. You may have been logged out.');
                appState.isLoggedIn = false;
                ui.updateLoginState();
            }
        },
        async renderAdminDashboard() {
            try {
                const adminData = await api.getAdminDashboardData();
                if (adminDueDateAlertsList && Array.isArray(adminData.due_date_alerts)) {
                    adminDueDateAlertsList.innerHTML = adminData.due_date_alerts.length ? adminData.due_date_alerts.map(book => `
                        <div class="p-4 bg-red-50 dark:bg-red-900 dark:bg-opacity-20 border-l-4 border-red-500 rounded-r-lg flex justify-between items-center">
                            <div>
                                <div class="font-semibold text-slate-800 dark:text-white">${book.title}</div>
                                <div class="text-sm text-slate-500 dark:text-gray-400">Borrower: ${book.user_name}</div>
                            </div>
                            <div class="text-sm text-red-600 dark:text-red-400 font-medium">
                                Due: ${new Date(book.due_date).toLocaleDateString()}
                            </div>
                        </div>
                    `).join('') : '<p class="text-slate-500 dark:text-gray-400 text-sm p-4">No books are overdue or due soon.</p>';
                }
                if (allBorrowedBooksList && Array.isArray(adminData.all_borrowed_books)) {
                    allBorrowedBooksList.innerHTML = adminData.all_borrowed_books.length ? adminData.all_borrowed_books.map(book => `
                        <div class="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
                            <div>
                                <div class="font-semibold text-slate-800 dark:text-white">${book.title}</div>
                                <div class="text-sm text-slate-500 dark:text-gray-400">Borrower: ${book.user_name}</div>
                            </div>
                            <div class="text-sm text-slate-600 dark:text-gray-300 font-medium">
                                Due: ${new Date(book.due_date).toLocaleDateString()}
                            </div>
                        </div>
                    `).join('') : '<p class="text-slate-500 dark:text-gray-400 text-sm p-4">No books are currently borrowed.</p>';
                }
            } catch (error) {
                console.error("Error rendering admin dashboard:", error);
                if (adminDueDateAlertsList) adminDueDateAlertsList.innerHTML = '<p class="text-red-500">Could not load dashboard data.</p>';
            }
        }
    };

    let html5QrCode;
    const startScanner = () => {
        scannerContainer.classList.remove('hidden');
        html5QrCode = new Html5Qrcode("qr-reader");
        const config = { fps: 10, qrbox: { width: 250, height: 150 } };
        html5QrCode.start({ facingMode: "environment" }, config, (decodedText) => {
            bookIdInput.value = decodedText;
            stopScanner();
        }).catch(err => {
            alert("Scanner error. Please grant camera permission.");
            console.error("Scanner failed to start:", err);
        });
    };
    const stopScanner = () => {
        if (html5QrCode && html5QrCode.isScanning) {
            html5QrCode.stop().then(() => scannerContainer.classList.add('hidden')).catch(err => console.error("Scanner stop failed", err));
        }
    };

    // --- EVENT LISTENERS (Admin forms) ---
    if (addBookForm) {
        addBookForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = { book_id: document.getElementById('new-book-id').value, title: document.getElementById('new-book-title').value, author: document.getElementById('new-book-author').value, };
            try {
                const result = await api.addBook(data);
                addBookStatus.textContent = result.message;
                addBookStatus.className = 'text-sm text-green-600';
                addBookForm.reset();
            } catch (error) {
                addBookStatus.textContent = error.message;
                addBookStatus.className = 'text-sm text-red-600';
            }
        });
    }
    if (addUserForm) {
        addUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const emailInput = document.getElementById('new-user-email').value.trim();
            const passwordInput = document.getElementById('new-user-password').value.trim();
            const userIdInput = document.getElementById('new-user-id').value.trim();
            const nameInput = document.getElementById('new-user-name').value.trim();
            if (!emailInput || !passwordInput || !userIdInput || !nameInput) {
                addUserStatus.textContent = "User ID, Name, Password, and Email are required.";
                addUserStatus.className = 'text-sm text-red-600';
                return;
            }
            const data = { user_id: userIdInput, name: nameInput, password: passwordInput, email: emailInput, rfid_uid: document.getElementById('new-user-rfid').value.trim(), };
            try {
                const result = await api.addUser(data);
                addUserStatus.textContent = result.message;
                addUserStatus.className = 'text-sm text-green-600';
                addUserForm.reset();
            } catch (error) {
                addUserStatus.textContent = error.message;
                addUserStatus.className = 'text-sm text-red-600';
            }
        });
    }
    if (removeUserForm) {
        removeUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userId = document.getElementById('remove-user-id').value;
            if (!userId) {
                removeUserStatus.textContent = "User ID is required.";
                removeUserStatus.className = 'text-sm text-red-600';
                return;
            }
            if (!confirm(`Are you sure you want to deactivate user ${userId}? This action cannot be undone.`)) { return; }
            try {
                const result = await api.removeUser(userId);
                removeUserStatus.textContent = result.message;
                removeUserStatus.className = 'text-sm text-green-600';
                removeUserForm.reset();
            } catch (error) {
                removeUserStatus.textContent = error.message;
                removeUserStatus.className = 'text-sm text-red-600';
            }
        });
    }
    if (reissueRfidForm) {
        reissueRfidForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = { user_id: document.getElementById('reissue-user-id').value, name: document.getElementById('reissue-user-name').value, new_rfid: document.getElementById('reissue-new-rfid').value, };
            try {
                const result = await api.reissueRfid(data);
                reissueRfidStatus.textContent = result.message;
                reissueRfidStatus.className = 'text-sm text-green-600';
                reissueRfidForm.reset();
            } catch (error) {
                reissueRfidStatus.textContent = error.message;
                reissueRfidStatus.className = 'text-sm text-red-600';
            }
        });
    }
    if (searchBookInput) {
        let searchTimeout;
        searchBookInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(async () => {
                const searchTerm = e.target.value;
                if (searchTerm.length < 3) { searchBookResults.innerHTML = ''; return; }
                try {
                    const result = await api.searchBook(searchTerm);
                    searchBookResults.innerHTML = result.books.length ? result.books.map(book => `<div class="dark:text-gray-300">${book.title} - <strong>${book.status}</strong></div>`).join('') : '<div>No books found.</div>';
                } catch (error) {
                    searchBookResults.innerHTML = '<div class="text-red-500">Search failed.</div>';
                }
            }, 300);
        });
    }

    // --- EVENT LISTENERS (Login, Logout, Navigation) ---
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userId = document.getElementById('user-id').value;
        const password = document.getElementById('password').value;
        const loginError = document.getElementById('login-error');
        try {
            const data = await api.login(userId, password);
            appState.isLoggedIn = true;
            appState.userName = data.user.name;
            appState.userId = userId;
            appState.userRole = data.user.role;
            loginError.textContent = '';
            if (appState.userRole === 'admin') {
                ui.showPage('adminAuth');
                startAuthPolling(true);
            } else {
                ui.updateLoginState();
            }
        } catch (error) {
            loginError.textContent = error.message;
        }
    });

    if(gotoForgotPasswordBtn) {
        gotoForgotPasswordBtn.addEventListener('click', () => ui.showPage('forgotPassword'));
    }
    if(gotoLoginBtn) {
        gotoLoginBtn.addEventListener('click', () => ui.showPage('login'));
    }

    async function handleLogout() {
        await api.logout();
        appState.isLoggedIn = false;
        appState.userName = '';
        appState.userId = '';
        appState.userRole = 'user';
        stopAuthPolling();
        ui.updateLoginState();
        loginForm.reset();
    }
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);
    if (adminLogoutBtn) adminLogoutBtn.addEventListener('click', handleLogout);
    if (adminDashboardLogoutBtn) adminDashboardLogoutBtn.addEventListener('click', handleLogout);
    if (gotoBorrowBtn) {
        gotoBorrowBtn.addEventListener('click', () => {
            bookIdInput.value = '';
            transactionStatus.innerHTML = '';
            ui.showPage('transaction');
            transactionTitle.textContent = 'Borrow a Book';
            transactionTypeSpan.textContent = 'Borrow';
            authStep.classList.remove('hidden');
            bookStep.classList.add('hidden');
            showAuthSpinner();
            startAuthPolling();
        });
    }
    if (gotoReturnBtn) {
        gotoReturnBtn.addEventListener('click', () => {
            bookIdInput.value = '';
            transactionStatus.innerHTML = '';
            ui.showPage('transaction');
            transactionTitle.textContent = 'Return a Book';
            transactionTypeSpan.textContent = 'Return';
            authStep.classList.remove('hidden');
            bookStep.classList.add('hidden');
            showAuthSpinner();
            startAuthPolling();
        });
    }
    function showAuthSpinner() {
        if (authSpinner) { authSpinner.classList.remove('hidden'); }
        if (authMessage) { authMessage.textContent = 'Please scan your RFID/ID card at the library kiosk to proceed.'; }
    }
    function hideAuthSpinner() {
        if (authSpinner) { authSpinner.classList.add('hidden'); }
    }
    
    // **MODIFIED**: Back Button Listener now calls deauthorize
    backBtns.forEach(btn => {
        btn.addEventListener('click', async () => { // Made async
            stopScanner();
            stopAuthPolling();
            hideAuthSpinner();
            
            // **NEW**: Invalidate the auth token on the server
            try {
                await api.deauthorize();
            } catch (error) {
                console.error("Could not deauthorize:", error);
            }
            
            ui.showDashboard();
        });
    });

    if (scanBtn) { scanBtn.addEventListener('click', startScanner); }
    if (stopScanBtn) { stopScanBtn.addEventListener('click', stopScanner); }
    
    if (confirmTransactionBtn) {
        confirmTransactionBtn.addEventListener('click', async () => {
            const bookId = bookIdInput.value.trim();
            if (!bookId) {
                transactionStatus.textContent = 'Please enter or scan a book ID.';
                transactionStatus.className = 'status-message text-red-500';
                return;
            }
            transactionStatus.textContent = 'Processing...';
            transactionStatus.className = 'status-message text-slate-500 dark:text-gray-400';
            try {
                const isBorrow = transactionTypeSpan.textContent === 'Borrow';
                const result = await (isBorrow ? api.borrowBook(bookId) : api.returnBook(bookId));
                
                transactionStatus.innerHTML = ''; 
                const msgP = document.createElement('p');
                msgP.textContent = result.message;
                transactionStatus.appendChild(msgP);
                
                if (result.message.includes('fine') || result.message.includes('Cannot')) {
                    transactionStatus.className = 'status-message text-red-600';
                } else {
                    transactionStatus.className = 'status-message text-green-600';
                }
                if (result.receipt_url) {
                    const receiptBtn = document.createElement('a');
                    receiptBtn.textContent = 'Download E-Receipt';
                    receiptBtn.href = result.receipt_url;
                    receiptBtn.target = '_blank';
                    receiptBtn.className = 'mt-2 inline-block bg-green-600 text-white font-semibold py-2 px-4 rounded-lg hover:bg-green-700';
                    transactionStatus.appendChild(receiptBtn);
                }
                setTimeout(() => {
                    stopScanner();
                    stopAuthPolling();
                    ui.showDashboard();
                    transactionStatus.innerHTML = '';
                }, 4000); 
            } catch (error) {
                transactionStatus.textContent = error.message;
                transactionStatus.className = 'status-message text-red-500';
            }
        });
    }

    // Dashboard Tab Listeners
    const allTabs = [tabBooksBtn, tabRecsBtn, tabSettingsBtn];
    const allContent = [contentBooks, contentRecs, contentSettings];

    allTabs.forEach((tab, index) => {
        if (tab) {
            tab.addEventListener('click', () => {
                // 1. Deactivate all tabs
                allTabs.forEach(t => {
                    t?.classList.remove('tab-active', 'text-slate-900', 'dark:text-white');
                    t?.classList.add('text-slate-500', 'border-transparent', 'dark:text-gray-400');
                });
                
                // 2. Hide all content
                allContent.forEach(c => c?.classList.add('hidden'));

                // 3. Activate the clicked tab
                tab.classList.add('tab-active', 'text-slate-900', 'dark:text-white');
                tab.classList.remove('text-slate-500', 'border-transparent', 'dark:text-gray-400');
                
                // 4. Show the corresponding content
                if (allContent[index]) {
                    allContent[index].classList.remove('hidden');
                }
            });
        }
    });

    // Password Form Handlers
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const oldPassword = document.getElementById('old-password').value;
            const newPassword = document.getElementById('new-password').value;
            changePasswordStatus.textContent = 'Updating...';
            changePasswordStatus.className = 'text-sm text-center text-slate-500 dark:text-gray-400';
            try {
                const result = await api.changePassword(oldPassword, newPassword);
                changePasswordStatus.textContent = result.message;
                changePasswordStatus.className = 'text-sm text-center text-green-600';
                changePasswordForm.reset();
            } catch (error) {
                changePasswordStatus.textContent = error.message;
                changePasswordStatus.className = 'text-sm text-center text-red-600';
            }
        });
    }

    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userId = document.getElementById('forgot-user-id').value;
            const email = document.getElementById('forgot-email').value;
            const newPassword = document.getElementById('forgot-new-password').value;
            forgotPasswordStatus.textContent = 'Resetting...';
            forgotPasswordStatus.className = 'text-sm text-center text-slate-500 dark:text-gray-400';
            try {
                const result = await api.forgotPassword(userId, email, newPassword);
                forgotPasswordStatus.textContent = result.message;
                forgotPasswordStatus.className = 'text-sm text-center text-green-600';
                forgotPasswordForm.reset();
            } catch (error) {
                forgotPasswordStatus.textContent = error.message;
                forgotPasswordStatus.className = 'text-sm text-center text-red-600';
            }
        });
    }


    // --- CHATBOT ---
    chatToggleBtn?.addEventListener('click', () => {
        chatWindow.classList.toggle('hidden');
        chatIconOpen.classList.toggle('hidden');
        chatIconClose.classList.toggle('hidden');
        if (!chatWindow.classList.contains('hidden')) {
            chatInput.focus();
            if (chatMessages.children.length === 0) appendBotMessage("Hello! I am the Library Assistant. How can I help you?");
        }
    });
    chatForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;
        appendUserMessage(message);
        chatInput.value = '';
        chatInput.disabled = true;
        appendBotMessage("Thinking...", true);
        try {
            const botResponse = await api.askChatbot(message);
            updateBotMessage(botResponse.response);
        } catch {
            updateBotMessage("Sorry, I'm having trouble connecting right now.");
        } finally {
            chatInput.disabled = false;
            chatInput.focus();
        }
    });
    function appendUserMessage(msg) {
        const div = document.createElement('div');
        div.className = 'flex justify-end mb-3';
        div.innerHTML = `<div class="bg-blue-600 text-white rounded-lg py-2 px-4 max-w-[80%]">${msg}</div>`;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    function appendBotMessage(msg, thinking = false) {
        const div = document.createElement('div');
        div.id = thinking ? 'thinking-bubble' : '';
        div.className = 'flex justify-start mb-3';
        div.innerHTML = `<div class="bg-slate-200 dark:bg-gray-700 ${thinking ? 'text-slate-500 italic' : 'text-slate-800 dark:text-white'} rounded-lg py-2 px-4 max-w-[80%]">${msg}</div>`;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    function updateBotMessage(msg) {
        const thinking = document.getElementById('thinking-bubble');
        if (thinking) {
            thinking.innerHTML = `<div class="bg-slate-200 dark:bg-gray-700 text-slate-800 dark:text-white rounded-lg py-2 px-4 max-w-[80%]">${msg}</div>`;
            thinking.id = '';
        } else appendBotMessage(msg);
    }
    function startAuthPolling(isAdminAuth = false) {
        stopAuthPolling(); 
        showAuthSpinner();
        setTimeout(() => {
            if (appState.authCheckInterval) return;
            appState.authCheckInterval = setInterval(async () => {
                if (!appState.isLoggedIn) { stopAuthPolling(); return; }
                try {
                    const status = await api.checkAuthStatus();
                    if (status.authorized) {
                        stopAuthPolling();
                        hideAuthSpinner();
                        if (isAdminAuth) {
                            adminWelcomeMessage.textContent = `Welcome, Admin ${appState.userName}!`;
                            ui.showPage('adminDashboard');
                            ui.renderAdminDashboard();
                        } else {
                            authStep.classList.add('hidden');
                            bookStep.classList.remove('hidden');
                        }
                    }
                } catch (error) {
                    console.error('Auth poll error:', error);
                    stopAuthPolling();
                    hideAuthSpinner();
                    handleLogout();
                }
            }, 2000);
        }, 100);
    }
    function stopAuthPolling() {
        if (appState.authCheckInterval) {
            clearInterval(appState.authCheckInterval);
            appState.authCheckInterval = null;
        }
    }
    adminTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            adminTabs.forEach(t => t.classList.remove('admin-tab-active'));
            tab.classList.add('admin-tab-active');
            adminTabContents.forEach(content => content.classList.add('hidden'));
            const contentId = tab.id.replace('tab', 'content');
            document.getElementById(contentId).classList.remove('hidden');
        });
    });

    // **MODIFIED**: New function to render the alert box
    function renderPaymentAlert(totalFineUSD) {
        paymentAlertContainer.innerHTML = ''; // Clear previous
        paymentAlertContainer.className = 'p-4 bg-red-50 dark:bg-red-900 dark:bg-opacity-30 border-l-4 border-red-500 rounded-r-lg shadow';

        const fineHeader = document.createElement('h3');
        fineHeader.className = "text-lg font-bold text-red-700 dark:text-red-300";
        fineHeader.textContent = `You have an outstanding fine of $${totalFineUSD.toFixed(2)}`;
        paymentAlertContainer.appendChild(fineHeader);
        
        const fineText = document.createElement('p');
        fineText.className = "text-sm text-red-600 dark:text-red-300 mt-1 mb-4";
        fineText.textContent = "Please pay your fine to borrow new books.";
        paymentAlertContainer.appendChild(fineText);

        const paypalBtnWrapper = document.createElement('div');
        paypalBtnWrapper.id = "paypal-btn-render-target";
        paypalBtnWrapper.className = "z-0 relative";
        paymentAlertContainer.appendChild(paypalBtnWrapper);
        
        paymentAlertContainer.classList.remove('hidden');

        try {
            paypal.Buttons({
                // **MODIFIED**: New style for the buttons
                style: {
                    layout: 'horizontal',
                    color: 'gold',
                    shape: 'rect',
                    label: 'paypal',
                    height: 40,
                    tagline: false
                },
                createOrder: async () => {
                    try {
                        const order = await api.paypalCreateOrder();
                        return order.id;
                    } catch (error) {
                        console.error('Error creating PayPal order:', error.message);
                        alert(`Error: ${error.message}`);
                        return null;
                    }
                },
                onApprove: async (data, actions) => {
                    try {
                        const captureDetails = await api.paypalCaptureOrder(data.orderID);
                        alert('Payment Successful! Your fines have been cleared.');
                        ui.renderUserDashboard(); 
                    } catch (error) {
                        console.error('Error capturing PayPal payment:', error.message);
                        alert(`Error: ${error.message}`);
                    }
                },
                onError: (err) => {
                    console.error('PayPal button error:', err);
                    alert('An error occurred with the PayPal button. Please try again.');
                }
            }).render('#paypal-btn-render-target');
        } catch (e) {
            console.error("PayPal SDK error:", e);
            paymentAlertContainer.innerHTML = "<p class='text-red-500'>Error loading payment buttons. Is your Client ID in index.html correct?</p>";
        }
    }
    
    // **REMOVED**: All old theme toggle logic

    // --- INITIALIZATION ---
    ui.updateLoginState();
    if (tabBooksBtn) tabBooksBtn.click(); // Default to "My Books" tab
    document.getElementById('admin-tab-overview')?.classList.add('admin-tab-active');
});