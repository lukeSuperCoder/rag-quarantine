const now = () => new Date().toISOString()

export const mockSources = [
  {
    chunk_id: 'chunk_entry_003',
    document_id: 'doc_entry',
    doc_name: '中华人民共和国携带宠物入境检疫要求',
    doc_type: 'entry_regulation',
    country: '中国',
    section_title: '隔离检疫',
    chunk_index: 3,
    score: 0.86,
    text: '携带入境的犬、猫应当接受海关现场检疫。来自非指定国家或地区、不能提供有效狂犬病抗体检测报告等情形的宠物，应进入隔离场进行隔离检疫。'
  },
  {
    chunk_id: 'chunk_port_001',
    document_id: 'doc_port',
    doc_name: '具备进境宠物隔离检疫条件的口岸名单',
    doc_type: 'port_list',
    country: '中国',
    section_title: '口岸名单',
    chunk_index: 1,
    score: 0.79,
    text: '部分指定口岸具备进境宠物隔离检疫条件，旅客应结合入境城市、宠物材料完整性和海关现场审核要求办理。'
  }
]

export const mockDocuments = [
  {
    id: 'doc_entry',
    filename: '中华人民共和国携带宠物入境检疫要求.doc',
    doc_name: '中华人民共和国携带宠物入境检疫要求',
    doc_type: 'entry_regulation',
    country: '中国',
    status: 'ready',
    chunk_count: 12,
    error_message: '',
    created_at: '2026-05-18T20:10:00+08:00',
    updated_at: '2026-05-18T20:14:00+08:00'
  },
  {
    id: 'doc_japan',
    filename: '赴日本犬猫检疫要求.docx',
    doc_name: '赴日本犬猫检疫要求',
    doc_type: 'country_export_req',
    country: '日本',
    status: 'ready',
    chunk_count: 8,
    error_message: '',
    created_at: '2026-05-18T20:20:00+08:00',
    updated_at: '2026-05-18T20:25:00+08:00'
  },
  {
    id: 'doc_lab',
    filename: '海关总署采信狂犬病抗体检测结果的实验室名单.doc',
    doc_name: '海关总署采信狂犬病抗体检测结果的实验室名单',
    doc_type: 'lab_list',
    country: '多国家',
    status: 'embedding',
    chunk_count: 24,
    error_message: '',
    created_at: '2026-05-21T19:40:00+08:00',
    updated_at: '2026-05-21T19:48:00+08:00'
  }
]

export const mockSessions = [
  {
    id: 'sess_demo',
    title: '宠物入境咨询',
    created_at: '2026-05-21T20:00:00+08:00',
    updated_at: '2026-05-21T20:10:00+08:00'
  }
]

export const mockMessages = {
  sess_demo: [
    {
      id: 'msg_demo_001',
      session_id: 'sess_demo',
      role: 'user',
      content: '宠物入境中国需要隔离多久？',
      sources: [],
      created_at: '2026-05-21T20:01:00+08:00'
    },
    {
      id: 'msg_demo_002',
      session_id: 'sess_demo',
      role: 'assistant',
      content: '根据现有政策材料，是否需要隔离主要取决于来源国家或地区、是否具备有效狂犬病抗体检测结果，以及入境口岸是否具备相关条件。材料不完整或不符合免隔离条件时，通常需要进入指定隔离场接受隔离检疫。',
      sources: mockSources,
      created_at: '2026-05-21T20:01:10+08:00'
    }
  ]
}

export function createMockSession(title = '新的宠物检疫咨询') {
  return {
    id: `sess_${Date.now()}`,
    title,
    created_at: now(),
    updated_at: now()
  }
}

export function createMockDocument(file, meta = {}) {
  const filename = file?.name || '新上传文档.docx'
  return {
    id: `doc_${Date.now()}`,
    filename,
    doc_name: filename.replace(/\.[^.]+$/, ''),
    doc_type: meta.doc_type || 'country_export_req',
    country: meta.country || '待识别',
    status: 'uploaded',
    chunk_count: 0,
    error_message: '',
    created_at: now(),
    updated_at: now()
  }
}
