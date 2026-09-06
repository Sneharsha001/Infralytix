/**
 * Infralytix — NewProjectModal Component.
 *
 * Glassmorphic modal for initializing a project workspace and uploading
 * repository zip archives for deterministic static intelligence analysis.
 */

import React, { useState } from 'react'
import { projectsApi } from '../api'
import { Project } from '../types'

interface NewProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: (project: Project) => void
}

export const NewProjectModal: React.FC<NewProjectModalProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [repoName, setRepoName] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (!file.name.toLowerCase().endsWith('.zip')) {
        setError('Please select a valid .zip repository archive.')
        setSelectedFile(null)
        return
      }
      setError(null)
      setSelectedFile(file)
      if (!name) {
        // Auto-fill project name from zip filename
        setName(file.name.replace(/\.zip$/i, ''))
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('Project name is required.')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      setStatusMessage('Creating project workspace...')

      const project = await projectsApi.create({
        name: name.trim(),
        description: description.trim() || undefined,
        repo_name: repoName.trim() || undefined,
      })

      if (selectedFile) {
        setStatusMessage('Uploading archive and running repository intelligence analysis...')
        const run = await projectsApi.uploadArchive(project.id, selectedFile)
        project.latest_run = run
      }

      onCreated(project)
      onClose()
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to create project. Please try again.'
      setError(msg)
    } finally {
      setIsSubmitting(false)
      setStatusMessage('')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="glass-card max-w-lg w-full p-6 sm:p-8 relative border border-white/15 shadow-2xl bg-neutral-900/90 max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          disabled={isSubmitting}
          className="absolute top-5 right-5 text-neutral-400 hover:text-white transition-colors"
          aria-label="Close"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Modal Header */}
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-brand-400 mb-1">
            <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
            Project Onboarding
          </div>
          <h3 className="text-xl font-bold text-white tracking-tight">
            Create Project Workspace
          </h3>
          <p className="text-xs text-neutral-400 mt-1">
            Initialize an isolated repository workspace and extract static code intelligence.
          </p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-neutral-300 mb-1.5">
              Project Name <span className="text-brand-400">*</span>
            </label>
            <input
              type="text"
              required
              disabled={isSubmitting}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Core API Service"
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-300 mb-1.5">
              Repository Name (optional)
            </label>
            <input
              type="text"
              disabled={isSubmitting}
              value={repoName}
              onChange={(e) => setRepoName(e.target.value)}
              placeholder="e.g. backend-service"
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-300 mb-1.5">
              Description (optional)
            </label>
            <textarea
              disabled={isSubmitting}
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of architecture or purpose..."
              className="input-field resize-none"
            />
          </div>

          {/* Repository Zip Upload Dropzone */}
          <div>
            <label className="block text-xs font-medium text-neutral-300 mb-1.5">
              Repository Archive (.zip)
            </label>
            <div className="border-2 border-dashed border-white/15 hover:border-brand-500/50 rounded-2xl p-4 text-center transition-colors bg-white/[0.02]">
              <input
                type="file"
                id="zip-upload"
                accept=".zip"
                disabled={isSubmitting}
                onChange={handleFileChange}
                className="hidden"
              />
              <label
                htmlFor="zip-upload"
                className="cursor-pointer flex flex-col items-center justify-center gap-2"
              >
                <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                {selectedFile ? (
                  <div>
                    <div className="text-xs font-medium text-emerald-400">{selectedFile.name}</div>
                    <div className="text-[10px] text-neutral-400">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyze
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="text-xs font-medium text-neutral-200">
                      Click to browse or drop your .zip archive here
                    </div>
                    <div className="text-[10px] text-neutral-400 mt-0.5">
                      Fast LOC calculation, language histogram & framework detection
                    </div>
                  </div>
                )}
              </label>
            </div>
          </div>

          {statusMessage && (
            <div className="p-3 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-full bg-brand-400 animate-ping" />
              <span>{statusMessage}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={onClose}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary text-xs shadow-brand"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processing...
                </span>
              ) : (
                'Create Project'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
