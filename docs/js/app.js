const App = (() => {
    const TEAM_FLAGS = {
        'Franca': '\u{1F1EB}\u{1F1F7}', 'Espanha': '\u{1F1EA}\u{1F1F8}',
        'Alemanha': '\u{1F1E9}\u{1F1EA}', 'Argentina': '\u{1F1E6}\u{1F1F7}',
        'Portugal': '\u{1F1F5}\u{1F1F9}', 'Inglaterra': '\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}',
        'Mexico': '\u{1F1F2}\u{1F1FD}', 'USA': '\u{1F1FA}\u{1F1F8}',
    };

    const TEAM_COLORS = {
        'Franca': '#002395', 'Espanha': '#C8102E', 'Alemanha': '#1a1a1a',
        'Argentina': '#75AADB', 'Portugal': '#006600', 'Inglaterra': '#CF081F',
        'Mexico': '#006847', 'USA': '#002868',
    };

    const OWNER_PHOTOS = {
        'Joao Victor Molina': 'photos/joao_molina.jpg',
        'Joao Victor Pires': 'photos/joao_pires.jpg',
        'Vinicius Lista': 'photos/vinicius_lista.jpg',
        'Igor Vereda': 'photos/igor_vereda.jpg',
        'Guilherme Rissi': 'photos/guilherme_rissi.jpg',
        'Kaiki Aguiar': 'photos/kaiki_aguiar.jpg',
        'Felipe Aguiar': 'photos/felipe_aguiar.jpg',
        'Reinaldo Urbano': 'photos/reinaldo_urbano.jpg',
    };

    const PHASE_LABELS = {
        'group': 'Fase de Grupos',
        'quarter_1v4': 'Quartas: 1o vs 4o',
        'quarter_2v3': 'Quartas: 2o vs 3o',
        'quarter_5v6': 'Quartas: 5o vs 6o',
        'upper_semi': 'Semifinal (chave superior)',
        'lower_r1': 'Chave inferior \u2014 1\u00aa rodada',
        'lower_r2': 'Chave inferior \u2014 2\u00aa rodada',
        'lower_final': 'Final da chave inferior',
        'grand_final': 'Grande final',
    };

    const cache = {};

    async function loadJSON(name) {
        if (cache[name]) return cache[name];
        try {
            const resp = await fetch(`data/${name}.json`);
            if (!resp.ok) return name === 'tournament_state' ? {} : [];
            const data = await resp.json();
            cache[name] = data;
            return data;
        } catch {
            return name === 'tournament_state' ? {} : [];
        }
    }

    function flag(teamName) {
        return TEAM_FLAGS[teamName] || '';
    }

    function teamLabel(teamName) {
        return `${flag(teamName)} ${teamName}`;
    }

    function teamColor(teamName) {
        return TEAM_COLORS[teamName] || '#00B4D8';
    }

    function ownerPhoto(ownerName) {
        return OWNER_PHOTOS[ownerName] || '';
    }

    function phaseLabel(phase) {
        return PHASE_LABELS[phase] || phase;
    }

    function el(id) {
        return document.getElementById(id);
    }

    function qs(sel) {
        return document.querySelector(sel);
    }

    function html(element, content) {
        if (typeof element === 'string') element = el(element);
        if (element) element.innerHTML = content;
    }

    function getParam(name) {
        return new URLSearchParams(window.location.search).get(name);
    }

    function computeStandings(matches, teams) {
        const teamMap = {};
        teams.forEach(t => {
            teamMap[t.id] = {
                team_id: t.id, team_name: t.name, owner: t.owner,
                played: 0, wins: 0, draws: 0, losses: 0,
                goals_for: 0, goals_against: 0, goal_difference: 0, points: 0, position: 0,
            };
        });

        matches.forEach(m => {
            if (!m.played || m.phase !== 'group') return;
            const h = teamMap[m.home_team_id], a = teamMap[m.away_team_id];
            if (!h || !a) return;
            h.played++; a.played++;
            h.goals_for += m.home_score || 0; h.goals_against += m.away_score || 0;
            a.goals_for += m.away_score || 0; a.goals_against += m.home_score || 0;
            if (m.home_score > m.away_score) { h.wins++; h.points += 3; a.losses++; }
            else if (m.home_score < m.away_score) { a.wins++; a.points += 3; h.losses++; }
            else { h.draws++; a.draws++; h.points++; a.points++; }
        });

        const rows = Object.values(teamMap);
        rows.forEach(r => r.goal_difference = r.goals_for - r.goals_against);
        rows.sort((a, b) => b.points - a.points || b.goal_difference - a.goal_difference || b.goals_for - a.goals_for);
        rows.forEach((r, i) => r.position = i + 1);
        return rows;
    }

    function getTopScorers(matches, limit = 10) {
        const goals = {};
        matches.forEach(m => {
            if (!m.played) return;
            (m.events || []).forEach(evt => {
                if (evt.type !== 'goal') return;
                if (!goals[evt.player_id]) {
                    goals[evt.player_id] = { player_id: evt.player_id, player_name: evt.player_name, team_id: evt.team_id, goals: 0 };
                }
                goals[evt.player_id].goals++;
            });
        });
        return Object.values(goals).sort((a, b) => b.goals - a.goals).slice(0, limit);
    }

    function getTopAssisters(matches, limit = 10) {
        const assists = {};
        matches.forEach(m => {
            if (!m.played) return;
            (m.events || []).forEach(evt => {
                if (evt.type !== 'assist') return;
                if (!assists[evt.player_id]) {
                    assists[evt.player_id] = { player_id: evt.player_id, player_name: evt.player_name, team_id: evt.team_id, assists: 0 };
                }
                assists[evt.player_id].assists++;
            });
        });
        return Object.values(assists).sort((a, b) => b.assists - a.assists).slice(0, limit);
    }

    function renderNav() {
        const path = window.location.pathname.split('/').pop() || 'index.html';
        const links = [
            ['index.html', 'Painel'], ['standings.html', 'Classificacao'], ['matches.html', 'Jogos'],
            ['bracket.html', 'Chaveamento'], ['teams.html', 'Selecoes'], ['formacao.html', 'Formacao'],
            ['transfers.html', 'Transferencias'], ['stats.html', 'Estatisticas'],
        ];
        const navLinks = links.map(([href, label]) => {
            const active = path === href || (path === '' && href === 'index.html');
            return `<a href="${href}" class="nav-link px-3 py-5 text-sm font-medium ${active ? 'active' : 'text-[#cbd5e1] hover:text-white'} transition">${label}</a>`;
        }).join('');

        html('header', `
            <div class="wc-gradient py-1.5">
                <div class="max-w-7xl mx-auto px-4 flex items-center justify-center gap-3 text-white text-xs font-medium tracking-wider">
                    <span>FIFA WORLD CUP 26</span>
                    <span class="opacity-40">|</span>
                    <span class="opacity-70">USA - MEXICO - CANADA</span>
                </div>
            </div>
            <nav class="bg-[#0f172a] border-b border-[#334155] sticky top-0 z-50">
                <div class="max-w-7xl mx-auto px-4">
                    <div class="flex items-center justify-between h-16">
                        <a href="index.html" class="flex items-center gap-3">
                            <span class="text-2xl">\u{1F3C6}</span>
                            <span class="text-lg font-bold text-white">Copa EA FC 26</span>
                        </a>
                        <div class="flex items-center gap-1">${navLinks}</div>
                    </div>
                </div>
            </nav>
        `);
    }

    function renderFooter() {
        html('footer', `
            <div class="wc-gradient-subtle border-t border-[#334155] py-6 mt-12">
                <div class="max-w-7xl mx-auto px-4 text-center">
                    <p class="text-[#64748b] text-sm">Copa EA FC 26 &mdash; FIFA World Cup 2026 Edition</p>
                    <p class="text-[#334155] text-xs mt-1">USA | Mexico | Canada</p>
                </div>
            </div>
        `);
    }

    function init() {
        renderNav();
        renderFooter();
    }

    return {
        init, loadJSON, flag, teamLabel, teamColor, phaseLabel, ownerPhoto,
        el, qs, html, getParam, computeStandings, getTopScorers, getTopAssisters,
        TEAM_FLAGS, TEAM_COLORS, PHASE_LABELS, OWNER_PHOTOS,
    };
})();
